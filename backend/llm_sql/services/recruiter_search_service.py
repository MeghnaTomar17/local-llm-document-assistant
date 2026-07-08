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

    def search(self, question: str, session_id: UUID | str | None = None) -> RecruiterSearchResponse:
        clean_question = str(question or "").strip()
        normalized_q = normalize_question(clean_question)
        logger.info("Starting recruiter search query=%s normalized=%s", clean_question, normalized_q)

        cached_generation = self._cached_generation(normalized_q)

        if cached_generation:
            generation = cached_generation
            validation = generation.validation
            logger.info("SQL cache hit for query=%s sql=%s", clean_question, generation.sql)
        else:
            generation = self.generator.generate(clean_question)
            logger.info(
                "SQL generation completed latency_seconds=%.3f sql=%s",
                generation.latency_seconds,
                generation.sql,
            )
            validation = generation.validation
            if validation.is_valid:
                self._cache_generation(normalized_q, generation.sql, validation)

        logger.info(
            "SQL validation completed is_valid=%s errors=%s",
            validation.is_valid,
            validation.errors,
        )

        if not validation.is_valid:
            logger.warning(
                "Generated SQL failed validation errors=%s sql=%s",
                validation.errors,
                generation.sql,
            )
            raise SQLSearchValidationError(validation.errors, generation.sql)

        execution = self.executor.execute(validation)

        logger.info(
            "Recruiter search completed question=%s sql=%s row_count=%s execution_time_ms=%.2f",
            clean_question,
            execution.generated_sql,
            execution.row_count,
            execution.execution_time_ms,
        )

        response = RecruiterSearchResponse(
            question=clean_question,
            generated_sql=execution.generated_sql,
            row_count=execution.row_count,
            execution_time_ms=execution.execution_time_ms,
            results=self._recruiter_results(execution.rows),
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
    def _recruiter_results(rows: list[dict]) -> list[RecruiterResumeResult | dict]:
        return [
            RecruiterSearchService._recruiter_result(row)
            for row in rows
        ]

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
