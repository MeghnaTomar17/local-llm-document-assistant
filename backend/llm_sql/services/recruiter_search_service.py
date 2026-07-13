from __future__ import annotations

import logging
from collections import OrderedDict
import os
import re
from threading import RLock
import time
from uuid import UUID

from backend.llm_sql.schemas import RecruiterResumeResult, RecruiterSearchResponse
from backend.llm_sql.services.candidate_ranker import CandidateRanker
from backend.llm_sql.services.query_relaxer import QueryRelaxer
from backend.llm_sql.services.search_debug import SearchDebugWriter
from backend.llm_sql.services.sql_executor import SQLExecutionResult, SQLExecutor
from backend.llm_sql.services.sql_generator import SQLGenerationResult, SQLGenerator
from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator, get_database_schema_metadata
from backend.llm_sql.services.requirement_preprocessor import preprocess_requirement
from backend.llm_sql.services.requirement_extractor import RequirementExtractor
from backend.llm_sql.services.requirement_validator import RequirementValidator
from database.crud import create_search_history


logger = logging.getLogger(__name__)
DEBUG_SEARCH = os.getenv("RECRUITER_SEARCH_DEBUG", "1").strip().lower() in {"1", "true", "yes", "on"}
SEARCH_MODEL_USED = "llama-requirement-extractor + deterministic-sql-builder"

_sql_cache: OrderedDict[str, tuple[float, str, SQLValidationResult, str, dict]] = OrderedDict()
_sql_cache_lock = RLock()
SQL_CACHE_TTL = 30.0
SQL_CACHE_MAX_SIZE = 128


def normalize_question(q: str) -> str:
    q = str(q or "").strip().lower()
    q = re.sub(r"[?.,!]", "", q)
    q = re.sub(r"\s+", " ", q).strip()
    return q


def normalize_candidate_type(candidate_type: str | None) -> str | None:
    value = str(candidate_type or "").strip().upper()
    return value if value in {"INTERNAL", "EXTERNAL"} else None


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
        extractor: RequirementExtractor | None = None,
        requirement_validator: RequirementValidator | None = None,
        query_relaxer: QueryRelaxer | None = None,
        ranker: CandidateRanker | None = None,
    ) -> None:
        self.validator = validator or SQLValidator()
        self.generator = generator or SQLGenerator(validator=self.validator)
        self.executor = executor or SQLExecutor()
        self.extractor = extractor or RequirementExtractor()
        self.requirement_validator = requirement_validator or RequirementValidator()
        self.query_relaxer = query_relaxer or QueryRelaxer()
        self.ranker = ranker or CandidateRanker()

    def search(
        self,
        question: str,
        session_id: UUID | str | None = None,
        candidate_type: str | None = None,
    ) -> RecruiterSearchResponse:
        started_all = time.perf_counter()
        if DEBUG_SEARCH:
            logger.info("Recruiter search query initiated: %s", str(question).encode("ascii", "ignore").decode("ascii"))

        debug = SearchDebugWriter(DEBUG_SEARCH)

        # 1. Stage 1: Requirement Cleaning
        t1_start = time.perf_counter()
        clean_question = preprocess_requirement(question)
        t1_end = time.perf_counter()
        cleaning_ms = (t1_end - t1_start) * 1000

        # 2. Stage 2: Requirement Extraction (LLM)
        t2_start = time.perf_counter()
        raw_json = self.extractor.extract(clean_question)
        t2_end = time.perf_counter()
        extraction_ms = (t2_end - t2_start) * 1000

        # 3. Stage 3: Skill Normalization
        t3_start = time.perf_counter()
        extracted_data = self.requirement_validator.validate_and_clean(raw_json)
        normalized_candidate_type = normalize_candidate_type(candidate_type)
        if normalized_candidate_type:
            extracted_data["candidate_type"] = normalized_candidate_type
        t3_end = time.perf_counter()
        normalization_ms = (t3_end - t3_start) * 1000

        # 4. Stage 4: SQL Generation
        t4_start = time.perf_counter()
        generation = self.generator.generate(extracted_data)
        sql = generation.sql
        t4_end = time.perf_counter()
        sql_generation_ms = (t4_end - t4_start) * 1000

        # 5. Stage 5: SQL Validation
        t5_start = time.perf_counter()
        validation = generation.validation
        t5_end = time.perf_counter()
        sql_validation_ms = (t5_end - t5_start) * 1000

        if not validation.is_valid:
            logger.warning("Generated SQL failed validation: %s", validation.errors)
            raise SQLSearchValidationError(validation.errors, sql)

        # 6. Stage 6: Database Retrieval with Fallback
        t6_start = time.perf_counter()
        execution = self.executor.execute(validation)
        
        # Deterministic retrieval fallback if no rows returned
        if execution.row_count == 0:
            logger.info("Database retrieval returned 0 rows. Running deterministic fallback query...")
            # Fallback 1: Relax hard filters (interview_marked, verified_only, candidate_type, fresher)
            relaxed_requirement = dict(extracted_data)
            relaxed_requirement["candidate_type"] = None
            relaxed_requirement["verified_only"] = None
            relaxed_requirement["interview_marked"] = None
            relaxed_requirement["fresher"] = None
            
            relaxed_sql = self.generator.builder.build_sql(relaxed_requirement)
            relaxed_val = self.validator.validate(relaxed_sql)
            logger.info("Fallback Stage 1: Relaxing hard filters. SQL: %s", relaxed_sql)
            execution = self.executor.execute(relaxed_val)
            
            # Fallback 2: Relax locations
            if execution.row_count == 0:
                logger.info("Fallback Stage 1 returned 0 rows. Fallback Stage 2: Relaxing locations...")
                relaxed_requirement["cities"] = []
                relaxed_requirement["locations"] = []
                relaxed_sql = self.generator.builder.build_sql(relaxed_requirement)
                relaxed_val = self.validator.validate(relaxed_sql)
                logger.info("Fallback Stage 2: Relaxing locations. SQL: %s", relaxed_sql)
                execution = self.executor.execute(relaxed_val)
                
            # Fallback 3: Return all candidates up to limit
            if execution.row_count == 0:
                logger.info("Fallback Stage 2 returned 0 rows. Fallback Stage 3: Fetching all resumes...")
                fallback_sql = f"SELECT {RECRUITER_COLUMNS}\nFROM resumes\nLIMIT {self.generator.builder.limit};"
                fallback_val = self.validator.validate(fallback_sql)
                execution = self.executor.execute(fallback_val)
                
        t6_end = time.perf_counter()
        sql_execution_ms = (t6_end - t6_start) * 1000

        # 7. Stage 7: Candidate Matching
        t7_start = time.perf_counter()
        results = self._recruiter_results(
            execution.rows,
            generated_sql=execution.generated_sql,
            candidate_type=candidate_type,
            requirement=extracted_data,
        )
        t7_end = time.perf_counter()
        matching_ms = (t7_end - t7_start) * 1000

        # 8. Stage 8: API Response & Stage Timing Logs
        total_time = (t7_end - t1_start)
        
        normalized_skills = self.generator.builder.get_normalized_skills(extracted_data) if hasattr(self.generator, "builder") else []
        
        logger.info("=" * 80)
        logger.info("RECRUITER SEARCH SUMMARY & STAGE TIMINGS")
        logger.info("=" * 80)
        logger.info("Requirement Cleaning    : %.1f ms", cleaning_ms)
        logger.info("Requirement Extraction  : %.2f s", extraction_ms / 1000)
        logger.info("Normalization           : %.1f ms", normalization_ms)
        logger.info("SQL Generation          : %.1f ms", sql_generation_ms)
        logger.info("SQL Validation          : %.1f ms", sql_validation_ms)
        logger.info("SQL Execution           : %.1f ms", sql_execution_ms)
        logger.info("Matching                : %.1f ms", matching_ms)
        logger.info("Total                   : %.2f s", total_time)
        logger.info("-" * 80)
        
        import json
        logger.info("Extracted Requirement JSON:\n%s", json.dumps(extracted_data, indent=2))
        logger.info("Normalized Skills: %s", normalized_skills)
        logger.info("Generated SQL:\n%s", execution.generated_sql)
        logger.info("SQL Row Count: %d", execution.row_count)
        logger.info("-" * 80)
        logger.info("Matched & Missing Skills per Candidate:")
        for idx, res in enumerate(results[:25]): # limit to top 25 to avoid log bloat
            if hasattr(res, "candidate_name"):
                candidate_name = res.candidate_name
                matched = res.matched_skills
                missing = res.missing_skills
            elif isinstance(res, dict):
                candidate_name = res.get("candidate_name")
                matched = res.get("matched_skills", [])
                missing = res.get("missing_skills", [])
            else:
                candidate_name = getattr(res, "candidate_name", "Unknown")
                matched = getattr(res, "matched_skills", [])
                missing = getattr(res, "missing_skills", [])

            logger.info("  %d. Candidate: %-25s | Matched Skills: %s | Missing Skills: %s", idx + 1, candidate_name or "Unnamed", matched, missing)
        logger.info("=" * 80)

        response = RecruiterSearchResponse(
            question=question,
            generated_sql=execution.generated_sql,
            row_count=execution.row_count,
            execution_time_ms=total_time * 1000,
            results=results,
            model_used="Deterministic SQL Builder",
            requirement_analysis=extracted_data,
            debug_report_path=debug.path,
            relaxation_attempts=[],
        )

        self._store_history(response, session_id)
        return response

    @staticmethod
    def _cached_generation(normalized_question: str) -> tuple[SQLGenerationResult, dict] | None:
        # Caching disabled to guarantee real-time query alignment with dynamic DB state
        return None

    @staticmethod
    def _cache_generation(
        normalized_question: str,
        sql: str,
        validation: SQLValidationResult,
        model: str | None = None,
        requirement: dict | None = None,
    ) -> None:
        # Caching disabled to guarantee real-time query alignment with dynamic DB state
        return

    def _execute_relaxed_searches(
        self,
        extracted_data: dict,
    ) -> tuple[SQLExecutionResult | None, SQLValidationResult | None, list[dict]]:
        attempts_log: list[dict] = []
        for attempt in self.query_relaxer.attempts(extracted_data):
            validation = self.validator.validate(attempt.sql)
            attempt_log = {
                "label": attempt.label,
                "reason": attempt.reason,
                "sql": attempt.sql,
                "valid": validation.is_valid,
                "errors": validation.errors,
                "row_count": 0,
            }
            if not validation.is_valid:
                attempts_log.append(attempt_log)
                continue

            execution = self.executor.execute(validation)
            attempt_log["row_count"] = execution.row_count
            attempt_log["execution_time_ms"] = execution.execution_time_ms
            attempts_log.append(attempt_log)

            if execution.row_count > 0:
                logger.info(
                    "Relaxed recruiter search succeeded attempt=%s row_count=%d",
                    attempt.label,
                    execution.row_count,
                )
                return execution, validation, attempts_log

        return None, None, attempts_log

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
                "model_used": response.model_used or SEARCH_MODEL_USED,
            }
        )

    def _recruiter_results(
        self,
        rows: list[dict],
        generated_sql: str = "",
        candidate_type: str | None = None,
        requirement: dict | None = None,
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
            except Exception as exc:
                logger.warning("Could not enrich recruiter results with interview metadata: %s", exc)
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

        results = self.ranker.rank(results, requirement or {}, candidate_type, order_cols)

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
