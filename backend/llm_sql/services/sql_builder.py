from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.llm_sql.services.query_relaxer import RECRUITER_COLUMNS
from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator


ALL_SKILL_FIELDS = (
    "mandatory_skills",
    "gis_skills",
    "programming_languages",
    "frameworks",
    "databases",
    "cloud",
    "tools",
    "preferred_skills",
)


@dataclass(frozen=True)
class SQLBuildResult:
    """Deterministically built SQL plus validation metadata."""

    sql: str
    validation: SQLValidationResult
    model: str = "deterministic-sql-builder"
    latency_seconds: float = 0.0
    validation_latency_seconds: float = 0.0


class SQLBuilder:
    """Build safe recruiter-search SQL from validated requirement JSON."""

    def __init__(self, validator: SQLValidator | None = None, limit: int = 200, max_skills: int = 8) -> None:
        self.validator = validator or SQLValidator()
        self.limit = min(max(int(limit), 1), 200)
        self.max_skills = max(int(max_skills), 1)

    def build(self, requirement: dict[str, Any]) -> SQLBuildResult:
        sql = self.build_sql(requirement)
        validation = self.validator.validate(sql)
        return SQLBuildResult(sql=sql, validation=validation)

    def build_sql(self, requirement: dict[str, Any]) -> str:
        filters: list[str] = []

        skills = self.get_normalized_skills(requirement)
        skill_filters = []
        for skill in skills:
            aliases = self._skill_aliases(requirement, skill)
            for alias in aliases:
                skill_filters.append(f"skills::text ILIKE '%{self._escape_like(alias)}%'")

        if skill_filters:
            filters.append("(" + " OR ".join(skill_filters) + ")")

        for city in self._list(requirement.get("cities") or requirement.get("locations")):
            filters.append(f"cities::text ILIKE '%{self._escape_like(city)}%'")

        candidate_type = str(requirement.get("candidate_type") or "").strip().upper()
        if candidate_type in {"INTERNAL", "EXTERNAL"}:
            filters.append(f"candidate_type = '{candidate_type}'")

        if requirement.get("verified_only") is True:
            filters.append("is_verified = true")

        if requirement.get("interview_marked") is True:
            filters.append("interview_marked = true")

        fresher = requirement.get("fresher")
        if fresher is True:
            filters.append("fresher = true")
        elif fresher is False or self._minimum_experience(requirement) is not None:
            filters.append("fresher = false")

        where = "\nWHERE " + "\nAND ".join(filters) if filters else ""
        return f"SELECT {RECRUITER_COLUMNS}\nFROM resumes{where}\nLIMIT {self.limit};"

    def get_normalized_skills(self, requirement: dict[str, Any]) -> list[str]:
        skills: list[str] = []
        seen: set[str] = set()
        for field in ALL_SKILL_FIELDS:
            for skill in self._list(requirement.get(field)):
                key = skill.lower()
                if key in seen:
                    continue
                seen.add(key)
                skills.append(skill)
        return skills[:self.max_skills]

    def _skill_aliases(self, requirement: dict[str, Any], skill: str) -> list[str]:
        expanded = requirement.get("expanded_skills")
        if isinstance(expanded, dict):
            aliases = expanded.get(skill)
            if isinstance(aliases, list):
                return self._unique([skill, *[str(alias) for alias in aliases]])
        return [skill]

    @staticmethod
    def _minimum_experience(requirement: dict[str, Any]) -> int | None:
        experience = requirement.get("experience")
        if isinstance(experience, dict):
            return experience.get("minimum_years") or experience.get("minimum")
        if isinstance(experience, int):
            return experience
        return None

    @staticmethod
    def _list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _escape_like(value: str) -> str:
        return str(value).replace("'", "''").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            clean = str(value or "").strip()
            key = clean.lower()
            if clean and key not in seen:
                seen.add(key)
                result.append(clean)
        return result
