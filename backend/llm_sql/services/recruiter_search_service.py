from __future__ import annotations

import logging

from backend.llm_sql.schemas import RecruiterSearchResponse
from backend.llm_sql.services.sql_executor import SQLExecutor
from backend.llm_sql.services.sql_generator import SQLGenerator
from backend.llm_sql.services.sql_validator import SQLValidator


logger = logging.getLogger(__name__)


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

    def search(self, question: str) -> RecruiterSearchResponse:
        clean_question = str(question or "").strip()
        logger.info("Starting recruiter search query.")
        logger.debug("Recruiter question: %s", clean_question)

        generation = self.generator.generate(clean_question)
        validation = self.validator.validate(generation.sql)

        if not validation.is_valid:
            logger.warning(
                "Generated SQL failed validation errors=%s sql=%s",
                validation.errors,
                generation.sql,
            )
            raise SQLSearchValidationError(validation.errors, generation.sql)

        execution = self.executor.execute(validation)

        logger.info(
            "Recruiter search completed row_count=%s execution_time_ms=%.2f",
            execution.row_count,
            execution.execution_time_ms,
        )

        return RecruiterSearchResponse(
            question=clean_question,
            generated_sql=execution.generated_sql,
            row_count=execution.row_count,
            execution_time_ms=execution.execution_time_ms,
            results=execution.rows,
        )
