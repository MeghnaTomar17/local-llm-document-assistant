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

ALLOWED_SELECT_COLUMNS = {
    "id",
    "candidate_name",
    "email",
    "phone_number",
    "skills",
    "cities",
    "fresher",
    "is_verified",
    "processing_status",
    "extraction_status",
    "uploaded_at",
    "updated_at",
    "notes",
    "hr_decision",
    "decision_at",
}

INTERNAL_COLUMNS = {
    "resume_hash",
    "stored_file_name",
    "file_path",
    "mime_type",
    "resume_blob",
}

AGGREGATE_FUNCTIONS = {
    "count",
    "sum",
    "avg",
    "min",
    "max",
}


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
                "Query references unknown table(s). Allowed table: resumes. "
                "Unknown table(s): " + ", ".join(sorted(unknown_tables))
            )

        if self._uses_select_star(normalized_sql):
            errors.append("SELECT * is not allowed. Select recruiter-facing columns explicitly.")

        boolean_select_expressions = self._boolean_select_expressions(normalized_sql)
        if boolean_select_expressions:
            errors.append(
                "Boolean filter expression(s) must be in WHERE, not SELECT: "
                + ", ".join(boolean_select_expressions)
            )

        unknown_columns = self._unknown_selected_columns(normalized_sql)
        if unknown_columns:
            errors.append(
                "Query selects column(s) that are not allowed in recruiter search results: "
                + ", ".join(sorted(unknown_columns))
            )

        internal_columns = self._selected_internal_columns(normalized_sql)
        if internal_columns:
            errors.append(
                "Query selects internal column(s) that must not be exposed: "
                + ", ".join(sorted(internal_columns))
            )

        if not self._is_aggregate_query(normalized_sql) and not self._has_limit(normalized_sql):
            errors.append("Non-aggregate recruiter search queries must include LIMIT 100.")

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

    @staticmethod
    def _uses_select_star(sql: str) -> bool:
        return bool(re.search(r"^\s*SELECT\s+\*", sql, flags=re.IGNORECASE))

    @staticmethod
    def _has_limit(sql: str) -> bool:
        return bool(re.search(r"\bLIMIT\s+\d+\b", sql, flags=re.IGNORECASE))

    @staticmethod
    def _is_aggregate_query(sql: str) -> bool:
        if re.search(r"\bGROUP\s+BY\b", sql, flags=re.IGNORECASE):
            return True

        return any(
            re.search(rf"\b{function}\s*\(", sql, flags=re.IGNORECASE)
            for function in AGGREGATE_FUNCTIONS
        )

    def _selected_columns(self, sql: str) -> set[str]:
        columns: set[str] = set()

        for expression in self._select_expressions(sql):
            column = self._base_column_name(expression)
            if column:
                columns.add(column)

        return columns

    def _select_expressions(self, sql: str) -> list[str]:
        select_match = re.search(
            r"^\s*SELECT\s+(.*?)\s+FROM\s+",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not select_match:
            return []

        selected = select_match.group(1)
        return self._split_select_expressions(selected)

    @staticmethod
    def _split_select_expressions(selected: str) -> list[str]:
        expressions: list[str] = []
        current: list[str] = []
        depth = 0

        for char in selected:
            if char == "(":
                depth += 1
            elif char == ")" and depth:
                depth -= 1

            if char == "," and depth == 0:
                expressions.append("".join(current).strip())
                current = []
                continue

            current.append(char)

        if current:
            expressions.append("".join(current).strip())

        return expressions

    @staticmethod
    def _base_column_name(expression: str) -> str | None:
        expression = re.sub(
            r"\s+AS\s+[a-zA-Z_][a-zA-Z0-9_]*\s*$",
            "",
            expression.strip(),
            flags=re.IGNORECASE,
        )
        expression = re.sub(
            r"\s+[a-zA-Z_][a-zA-Z0-9_]*\s*$",
            "",
            expression.strip(),
        )
        expression = expression.strip('"')

        if re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", expression):
            return expression.lower()

        qualified_match = re.match(
            r"^(?:[a-zA-Z_][a-zA-Z0-9_]*\.)?([a-zA-Z_][a-zA-Z0-9_]*)$",
            expression,
        )
        if qualified_match:
            return qualified_match.group(1).lower()

        function_match = re.match(
            r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
            expression,
            flags=re.IGNORECASE,
        )
        if function_match and function_match.group(1).lower() in AGGREGATE_FUNCTIONS:
            return None

        return None

    def _unknown_selected_columns(self, sql: str) -> set[str]:
        selected_columns = self._selected_columns(sql)
        return {
            column
            for column in selected_columns
            if column not in ALLOWED_SELECT_COLUMNS and column not in INTERNAL_COLUMNS
        }

    def _selected_internal_columns(self, sql: str) -> set[str]:
        return self._selected_columns(sql) & INTERNAL_COLUMNS

    def _boolean_select_expressions(self, sql: str) -> list[str]:
        bad_expressions = []

        for expression in self._select_expressions(sql):
            if self._is_boolean_select_expression(expression):
                bad_expressions.append(expression)

        return bad_expressions

    @staticmethod
    def _is_boolean_select_expression(expression: str) -> bool:
        expression = re.sub(
            r"\s+AS\s+[a-zA-Z_][a-zA-Z0-9_]*\s*$",
            "",
            expression.strip(),
            flags=re.IGNORECASE,
        )

        return bool(
            re.search(
                r"(?:\bILIKE\b|\bLIKE\b|\bSIMILAR\s+TO\b|"
                r"\bIS\s+NULL\b|\bIS\s+NOT\s+NULL\b|\bIN\s*\(|"
                r"\bBETWEEN\b|=|<>|!=|<=|>=|<|>)",
                expression,
                flags=re.IGNORECASE,
            )
        )
