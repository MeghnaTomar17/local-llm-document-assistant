from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import base64
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from database.connection import SessionLocal
from backend.llm_sql.services.sql_validator import SQLValidationResult


logger = logging.getLogger(__name__)


class SQLExecutionError(RuntimeError):
    """Raised when a validated SELECT query cannot be executed."""


class SQLValidationRequiredError(ValueError):
    """Raised when execution is attempted with invalid or unvalidated SQL."""


@dataclass(frozen=True)
class SQLExecutionResult:
    """Structured result returned after executing a read-only SELECT query."""

    generated_sql: str
    row_count: int
    execution_time_ms: float
    rows: list[dict[str, Any]] = field(default_factory=list)


class SQLExecutor:
    """Execute already validated read-only SQL using the project database session."""

    def __init__(self, session_factory: sessionmaker = SessionLocal) -> None:
        self.session_factory = session_factory

    def execute(self, validation: SQLValidationResult) -> SQLExecutionResult:
        """Execute SQL that has already passed SQLValidator validation."""

        if not isinstance(validation, SQLValidationResult):
            raise SQLValidationRequiredError(
                "SQLExecutor.execute expects a SQLValidationResult."
            )

        if not validation.is_valid:
            raise SQLValidationRequiredError(
                "Cannot execute SQL that failed validation: "
                + "; ".join(validation.errors)
            )

        sql = validation.sql.strip()
        started_at = time.perf_counter()

        logger.info("Executing validated recruiter SQL.")
        logger.debug("Recruiter SQL: %s", sql)

        session = self.session_factory()
        try:
            with session.begin():
                session.execute(text("SET TRANSACTION READ ONLY"))
                result = session.execute(text(sql))
                rows = [
                    self._json_safe_row(dict(row))
                    for row in result.mappings().all()
                ]

            execution_time_ms = (time.perf_counter() - started_at) * 1000
            logger.info(
                "Executed recruiter SQL in %.2fms row_count=%s",
                execution_time_ms,
                len(rows),
            )

            return SQLExecutionResult(
                generated_sql=sql,
                row_count=len(rows),
                execution_time_ms=execution_time_ms,
                rows=rows,
            )

        except SQLAlchemyError as exc:
            session.rollback()
            execution_time_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "Failed to execute recruiter SQL after %.2fms.",
                execution_time_ms,
            )
            raise SQLExecutionError("Failed to execute recruiter SQL.") from exc

        finally:
            session.close()

    @classmethod
    def _json_safe_row(cls, row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: cls._json_safe_value(value)
            for key, value in row.items()
        }

    @classmethod
    def _json_safe_value(cls, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, UUID):
            return str(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, bytes):
            return {
                "encoding": "base64",
                "size_bytes": len(value),
                "data": base64.b64encode(value).decode("ascii"),
            }

        if isinstance(value, list):
            return [cls._json_safe_value(item) for item in value]

        if isinstance(value, tuple):
            return [cls._json_safe_value(item) for item in value]

        if isinstance(value, dict):
            return {
                str(key): cls._json_safe_value(item)
                for key, item in value.items()
            }

        return str(value)
