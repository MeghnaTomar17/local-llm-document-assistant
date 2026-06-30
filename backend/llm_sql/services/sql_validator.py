from __future__ import annotations

from dataclasses import dataclass, field
import re


FORBIDDEN_SQL_KEYWORDS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "DO",
)


@dataclass(frozen=True)
class SQLValidationResult:
    """Structured result returned by SQLValidator."""

    is_valid: bool
    sql: str
    errors: list[str] = field(default_factory=list)


class SQLValidator:
    """Validate generated SQL before any future execution step."""

    def __init__(self, allowed_tables: set[str] | None = None) -> None:
        self.allowed_tables = allowed_tables or {"resumes"}

    def validate(self, sql: str) -> SQLValidationResult:
        """Return a structured validation result for generated SQL."""

        normalized_sql = self._normalize(sql)
        errors: list[str] = []

        if not normalized_sql:
            errors.append("SQL is empty.")
            return SQLValidationResult(False, normalized_sql, errors)

        if not self._starts_with_select(normalized_sql):
            errors.append("SQL must begin with SELECT.")

        if self._has_multiple_statements(normalized_sql):
            errors.append("Multiple SQL statements are not allowed.")

        forbidden = self._forbidden_keywords(normalized_sql)
        if forbidden:
            errors.append(
                "Forbidden SQL keyword(s): " + ", ".join(sorted(forbidden))
            )

        unknown_tables = self._unknown_tables(normalized_sql)
        if unknown_tables:
            errors.append(
                "Unknown table(s): " + ", ".join(sorted(unknown_tables))
            )

        return SQLValidationResult(
            is_valid=not errors,
            sql=normalized_sql,
            errors=errors,
        )

    @staticmethod
    def _normalize(sql: str) -> str:
        sql = str(sql or "").strip()
        sql = re.sub(r"\s+", " ", sql)
        return sql

    @staticmethod
    def _starts_with_select(sql: str) -> bool:
        return bool(re.match(r"^\s*SELECT\b", sql, flags=re.IGNORECASE))

    @staticmethod
    def _has_multiple_statements(sql: str) -> bool:
        stripped = sql.strip()
        without_final_semicolon = stripped[:-1] if stripped.endswith(";") else stripped
        return ";" in without_final_semicolon

    @staticmethod
    def _forbidden_keywords(sql: str) -> set[str]:
        return {
            keyword
            for keyword in FORBIDDEN_SQL_KEYWORDS
            if re.search(rf"\b{keyword}\b", sql, flags=re.IGNORECASE)
        }

    def _unknown_tables(self, sql: str) -> set[str]:
        table_matches = re.findall(
            r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b",
            sql,
            flags=re.IGNORECASE,
        )
        return {
            table
            for table in table_matches
            if table.lower() not in self.allowed_tables
        }
