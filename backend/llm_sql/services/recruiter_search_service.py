from __future__ import annotations

import logging
from uuid import UUID

from backend.llm_sql.schemas import RecruiterResumeResult, RecruiterSearchResponse
from backend.llm_sql.services.sql_executor import SQLExecutor
from backend.llm_sql.services.sql_generator import SQLGenerator
from backend.llm_sql.services.sql_validator import SQLValidator
from database.crud import create_search_history


logger = logging.getLogger(__name__)
SEARCH_MODEL_USED = "qwen2.5-coder"


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
        logger.info("Starting recruiter search query=%s", clean_question)

        generation = self.generator.generate(clean_question)
        logger.info(
            "SQL generation completed latency_seconds=%.3f sql=%s",
            generation.latency_seconds,
            generation.sql,
        )

        validation = self.validator.validate(generation.sql)
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
