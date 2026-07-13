from __future__ import annotations

from dataclasses import dataclass
import time

from backend.llm_sql.services.sql_builder import SQLBuilder
from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator


class SQLGenerationError(RuntimeError):
    """Raised when deterministic SQL generation cannot be completed."""


@dataclass(frozen=True)
class SQLGeneratorConfig:
    """Compatibility config retained for older imports.

    SQL generation is deterministic now; model and Ollama settings are ignored.
    """

    model: str = "deterministic-sql-builder"
    ollama_url: str = "disabled"
    timeout_seconds: float = 0.0
    max_skills: int = 8

    @classmethod
    def from_env(cls) -> "SQLGeneratorConfig":
        import os
        try:
            max_skills = int(os.getenv("SQL_MAX_SKILLS", "8"))
        except ValueError:
            max_skills = 8
        return cls(max_skills=max_skills)


@dataclass(frozen=True)
class SQLGenerationResult:
    """Built SQL plus validation metadata."""

    sql: str
    validation: SQLValidationResult
    model: str
    latency_seconds: float
    validation_latency_seconds: float = 0.0


class SQLGenerator:
    """Compatibility wrapper around the deterministic SQLBuilder."""

    def __init__(
        self,
        config: SQLGeneratorConfig | None = None,
        validator: SQLValidator | None = None,
    ) -> None:
        self.config = config or SQLGeneratorConfig.from_env()
        self.validator = validator or SQLValidator()
        self.builder = SQLBuilder(validator=self.validator, max_skills=self.config.max_skills)

    def generate_sql(self, requirement: dict) -> str:
        return self.generate(requirement).sql

    def generate(self, requirement: dict, use_direct_prompt: bool = False) -> SQLGenerationResult:
        if not isinstance(requirement, dict):
            raise SQLGenerationError("Validated requirement JSON is required for deterministic SQL building.")

        started = time.perf_counter()
        result = self.builder.build(requirement)
        latency = time.perf_counter() - started
        return SQLGenerationResult(
            sql=result.sql,
            validation=result.validation,
            model=self.config.model,
            latency_seconds=latency,
            validation_latency_seconds=result.validation_latency_seconds,
        )

    @staticmethod
    def clean_sql(raw_sql: str) -> str:
        return str(raw_sql or "").strip()
