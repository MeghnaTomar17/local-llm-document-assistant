from __future__ import annotations

import logging
from collections import OrderedDict
import re
from threading import RLock
import time
from uuid import UUID

from backend.llm_sql.schemas import RecruiterResumeResult, RecruiterSearchResponse
from backend.llm_sql.services.sql_executor import SQLExecutor
from backend.llm_sql.services.sql_generator import SQLGenerationResult, SQLGenerator
from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator, get_database_schema_metadata
from backend.llm_sql.services.requirement_preprocessor import preprocess_requirement
from database.crud import create_search_history


logger = logging.getLogger(__name__)
SEARCH_MODEL_USED = "qwen2.5-coder"

_sql_cache: OrderedDict[str, tuple[float, str, SQLValidationResult]] = OrderedDict()
_sql_cache_lock = RLock()
SQL_CACHE_TTL = 30.0
SQL_CACHE_MAX_SIZE = 128


def normalize_question(q: str) -> str:
    q = str(q or "").strip().lower()
    q = re.sub(r"[?.,!]", "", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


class SQLSearchValidationError(ValueError):
    """Raised when generated SQL does not pass validation."""

    def __init__(self, errors: list[str], generated_sql: str) -> None:
        self.errors = errors
        self.generated_sql = generated_sql
        super().__init__("; ".join(errors))


class RecruiterSearchService:
    """Run the natural-language recruiter search pipeline."""

    def __init__(
        self,
        generator: SQLGenerator | None = None,
        validator: SQLValidator | None = None,
        executor: SQLExecutor | None = None,
    ) -> None:
        self.validator = validator or SQLValidator()
        self.generator = generator or SQLGenerator(validator=self.validator)
        self.executor = executor or SQLExecutor()

    def search(
        self,
        question: str,
        session_id: UUID | str | None = None,
        candidate_type: str | None = None,
    ) -> RecruiterSearchResponse:
        started_all = time.perf_counter()

        # 1. Preprocess requirement
        raw_prompt_size = len(question or "")
        clean_question = preprocess_requirement(question)
        cleaned_prompt_size = len(clean_question)

        normalized_q = normalize_question(clean_question)
        logger.info(
            "Starting recruiter search raw_prompt_size=%d cleaned_prompt_size=%d",
            raw_prompt_size,
            cleaned_prompt_size,
        )

        cached_generation = self._cached_generation(normalized_q)

        gen_start = time.perf_counter()
        if cached_generation:
            generation = cached_generation
            validation = generation.validation
            logger.info("SQL cache hit for preprocessed query")
        else:
            generation = self.generator.generate(clean_question)
            validation = generation.validation
            if validation.is_valid:
                self._cache_generation(normalized_q, generation.sql, validation)
        gen_time = time.perf_counter() - gen_start

        if not validation.is_valid:
            logger.warning(
                "Generated SQL failed validation errors=%s sql=%s",
                validation.errors,
                generation.sql,
            )
            raise SQLSearchValidationError(validation.errors, generation.sql)

        exec_start = time.perf_counter()
        execution = self.executor.execute(validation)
        exec_time = time.perf_counter() - exec_start

        rank_start = time.perf_counter()
        results = self._recruiter_results(execution.rows, generation.sql, candidate_type)
        rank_time = time.perf_counter() - rank_start

        total_time = time.perf_counter() - started_all

        logger.info(
            "Recruiter search performance metrics: "
            "Raw Prompt Size (characters): %d | "
            "Cleaned Prompt Size (characters): %d | "
            "SQL Generation Time: %.3fs | "
            "SQL Execution Time: %.3fs | "
            "Ranking Time: %.3fs | "
            "Total Time: %.3fs",
            raw_prompt_size,
            cleaned_prompt_size,
            gen_time,
            exec_time,
            rank_time,
            total_time,
        )

        response = RecruiterSearchResponse(
            question=question,
            generated_sql=execution.generated_sql,
            row_count=execution.row_count,
            execution_time_ms=execution.execution_time_ms,
            results=results,
            model_used=generation.model or SEARCH_MODEL_USED,
        )

        self._store_history(response, session_id)
        return response

    @staticmethod
    def _cached_generation(normalized_question: str) -> SQLGenerationResult | None:
        if not normalized_question:
            return None
        now = time.time()
        with _sql_cache_lock:
            cached = _sql_cache.get(normalized_question)
            if not cached:
                return None

            cached_at, sql, validation = cached
            if now - cached_at >= SQL_CACHE_TTL:
                del _sql_cache[normalized_question]
                return None

            _sql_cache.move_to_end(normalized_question)
            generation = SQLGenerationResult(
                sql=sql,
                validation=validation,
                model=SEARCH_MODEL_USED,
                latency_seconds=0.0,
            )
            return generation

    @staticmethod
    def _cache_generation(normalized_question: str, sql: str, validation: SQLValidationResult) -> None:
        if not normalized_question or not validation.is_valid:
            return

        with _sql_cache_lock:
            _sql_cache[normalized_question] = (time.time(), sql, validation)
            _sql_cache.move_to_end(normalized_question)
            while len(_sql_cache) > SQL_CACHE_MAX_SIZE:
                _sql_cache.popitem(last=False)

    @staticmethod
    def _store_history(response: RecruiterSearchResponse, session_id: UUID | str | None) -> None:
        create_search_history(
            {
                "session_id": session_id,
                "query": response.question,
                "generated_sql": response.generated_sql,
                "result_count": response.row_count,
                "results_snapshot": [
                    result.model_dump(mode="json") if hasattr(result, "model_dump") else result
                    for result in response.results
                ],
                "execution_time_ms": response.execution_time_ms,
                "model_used": SEARCH_MODEL_USED,
            }
        )

    @staticmethod
    def _recruiter_results(
        rows: list[dict],
        generated_sql: str = "",
        candidate_type: str | None = None,
    ) -> list[RecruiterResumeResult | dict]:
        resume_ids = []
        for r in rows:
            rid = r.get("id")
            if rid:
                try:
                    resume_ids.append(UUID(str(rid)))
                except ValueError:
                    pass

        interview_map = {}
        if resume_ids:
            from database.connection import SessionLocal
            from database.models import Resume
            from sqlalchemy import select
            db = SessionLocal()
            try:
                res = db.execute(select(Resume.id, Resume.interview_marked, Resume.candidate_type).where(Resume.id.in_(resume_ids))).all()
                interview_map = {row.id: (row.interview_marked, row.candidate_type) for row in res}
            except Exception:
                pass
            finally:
                db.close()

        results = []
        for row in rows:
            rid = row.get("id")
            try:
                uuid_id = UUID(str(rid)) if rid else None
                row_copy = dict(row)
                cached = interview_map.get(uuid_id)
                if cached:
                    row_copy["interview_marked"] = cached[0]
                    row_copy["candidate_type"] = cached[1]
                else:
                    row_copy["interview_marked"] = False
                    row_copy["candidate_type"] = "EXTERNAL"
                results.append(row_copy)
            except ValueError:
                row_copy = dict(row)
                row_copy["interview_marked"] = False
                row_copy["candidate_type"] = "EXTERNAL"
                row_copy["candidate_type"] = "EXTERNAL"
                results.append(row_copy)

        # 1. Parse ORDER BY columns
        order_cols = []
        if generated_sql:
            match = re.search(
                r"\bORDER\s+BY\s+(.*?)(?:\bLIMIT\b|$)",
                generated_sql,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if match:
                order_by_text = match.group(1).strip()
                for part in order_by_text.split(","):
                    part_clean = part.strip().split()[0]
                    if "." in part_clean:
                        part_clean = part_clean.split(".")[-1]
                    part_clean = part_clean.strip('"`')
                    order_cols.append(part_clean.lower())

        # 2. Score tie-breaker metadata
        def get_tie_breaker_score(r: dict) -> float:
            score = 0.0
            if r.get("interview_marked"):
                score += 3.0
            if candidate_type:
                c_type = r.get("candidate_type") or "EXTERNAL"
                if c_type.upper() == candidate_type.upper():
                    score += 2.0
            if r.get("is_verified"):
                score += 1.0

            uploaded_at = r.get("uploaded_at")
            if uploaded_at:
                from datetime import datetime
                dt = None
                if isinstance(uploaded_at, str):
                    try:
                        dt = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
                    except Exception:
                        pass
                elif isinstance(uploaded_at, datetime):
                    dt = uploaded_at

                if dt:
                    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
                    diff = (now - dt).days
                    if diff <= 7:
                        score += 1.0
                    elif diff <= 30:
                        score += 0.5
                    else:
                        score += 0.1
            return score

        # 3. Sort by tie-breaker
        if order_cols:
            groups = []
            current_key = None
            current_group = []
            for r in results:
                key = tuple(r.get(col) for col in order_cols)
                if current_key is None or key == current_key:
                    current_group.append(r)
                    current_key = key
                else:
                    groups.append(current_group)
                    current_group = [r]
                    current_key = key
            if current_group:
                groups.append(current_group)

            ranked_results = []
            for group in groups:
                group.sort(key=get_tie_breaker_score, reverse=True)
                ranked_results.extend(group)
            results = ranked_results
        else:
            results.sort(key=get_tie_breaker_score, reverse=True)

        return [RecruiterSearchService._recruiter_result(r) for r in results]

    @staticmethod
    def _recruiter_result(row: dict) -> RecruiterResumeResult | dict:
        recruiter_fields = set(RecruiterResumeResult.model_fields)

        if "id" not in row:
            return row

        return RecruiterResumeResult.model_validate(
            {
                key: value
                for key, value in row.items()
                if key in recruiter_fields
            }
        )


_recruiter_search_service_instance = None
_recruiter_search_service_lock = RLock()


def get_recruiter_search_service() -> RecruiterSearchService:
    global _recruiter_search_service_instance
    if _recruiter_search_service_instance is None:
        with _recruiter_search_service_lock:
            if _recruiter_search_service_instance is None:
                _recruiter_search_service_instance = RecruiterSearchService()
    return _recruiter_search_service_instance


def warm_recruiter_search_service() -> RecruiterSearchService:
    service = get_recruiter_search_service()
    get_database_schema_metadata()
    return service
