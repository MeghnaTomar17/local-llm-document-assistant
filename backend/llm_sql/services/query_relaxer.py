from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any


RECRUITER_COLUMNS = (
    "id, candidate_name, email, phone_number, skills, cities, fresher, "
    "is_verified, processing_status, extraction_status, uploaded_at, updated_at, "
    "hr_notes, technical_notes, final_notes, hr_decision, decision_at, "
    "interview_marked, candidate_type"
)

SKILL_FIELDS = (
    "mandatory_skills",
    "gis_skills",
    "programming_languages",
    "frameworks",
    "databases",
    "cloud",
    "tools",
)


@dataclass(frozen=True)
class RelaxationAttempt:
    label: str
    reason: str
    requirement: dict[str, Any]
    sql: str


class QueryRelaxer:
    """Build deterministic fallback SQL attempts when strict SQL returns zero rows."""

    def attempts(self, requirement: dict[str, Any]) -> list[RelaxationAttempt]:
        base = deepcopy(requirement or {})
        attempts: list[RelaxationAttempt] = []

        without_preferred = deepcopy(base)
        without_preferred["preferred_skills"] = []
        attempts.append(self._attempt("remove_preferred_skills", "Removed preferred skills.", without_preferred))

        mandatory_less_strict = deepcopy(without_preferred)
        mandatory_skills = self._unique_skills(mandatory_less_strict)
        if len(mandatory_skills) > 2:
            keep = mandatory_skills[: max(2, len(mandatory_skills) - 1)]
            mandatory_less_strict = self._set_skill_fields(mandatory_less_strict, keep)
            attempts.append(
                self._attempt(
                    "reduce_mandatory_skills",
                    "Reduced mandatory skill filters.",
                    mandatory_less_strict,
                )
            )

        skill_or = deepcopy(without_preferred)
        attempts.append(
            self._attempt(
                "skill_or_search",
                "Matched any key skill instead of requiring every skill.",
                skill_or,
                skill_mode="OR",
            )
        )

        no_experience = deepcopy(skill_or)
        no_experience["experience"] = {"minimum_years": None, "maximum_years": None}
        no_experience["fresher"] = None
        attempts.append(
            self._attempt(
                "remove_experience_constraint",
                "Removed experience/fresher constraint.",
                no_experience,
                skill_mode="OR",
            )
        )

        keyword_only = deepcopy(no_experience)
        keyword_only["locations"] = []
        keyword_only["candidate_type"] = None
        keyword_only["verified_only"] = None
        keyword_only["interview_marked"] = None
        attempts.append(
            self._attempt(
                "keyword_search_only",
                "Used broad keyword-only skill search.",
                keyword_only,
                skill_mode="OR",
                include_non_skill_filters=False,
            )
        )

        seen_sql: set[str] = set()
        unique_attempts: list[RelaxationAttempt] = []
        for attempt in attempts:
            if attempt.sql in seen_sql:
                continue
            seen_sql.add(attempt.sql)
            unique_attempts.append(attempt)
        return unique_attempts

    def possible_zero_row_reasons(self, requirement: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        skills = self._unique_skills(requirement)
        if len(skills) >= 3:
            reasons.append("Skills filter may be too strict because several skill conditions were combined.")
        if self._experience_minimum(requirement) is not None or requirement.get("fresher") is not None:
            reasons.append("Experience or fresher constraint may exclude matching candidates.")
        if requirement.get("locations"):
            reasons.append("City/location filter may not match extracted resume cities.")
        if requirement.get("candidate_type"):
            reasons.append("Candidate pool filter may exclude otherwise matching profiles.")
        if not reasons:
            reasons.append("No resume metadata matched the extracted requirement terms.")
        return reasons

    def _attempt(
        self,
        label: str,
        reason: str,
        requirement: dict[str, Any],
        skill_mode: str = "AND",
        include_non_skill_filters: bool = True,
    ) -> RelaxationAttempt:
        return RelaxationAttempt(
            label=label,
            reason=reason,
            requirement=requirement,
            sql=self.build_sql(requirement, skill_mode, include_non_skill_filters),
        )

    def build_sql(
        self,
        requirement: dict[str, Any],
        skill_mode: str = "AND",
        include_non_skill_filters: bool = True,
    ) -> str:
        filters: list[str] = []
        skill_filters = [
            self._skill_filter(requirement, skill)
            for skill in self._unique_skills(requirement)
        ]
        if skill_filters:
            joiner = " OR " if skill_mode.upper() == "OR" else " AND "
            filters.append("(" + joiner.join(skill_filters) + ")")

        if include_non_skill_filters:
            for city in self._list(requirement.get("locations") or requirement.get("cities")):
                filters.append(f"cities::text ILIKE '%{self._escape_like(city)}%'")

            candidate_type = str(requirement.get("candidate_type") or "").upper()
            if candidate_type in {"INTERNAL", "EXTERNAL"}:
                filters.append(f"candidate_type = '{candidate_type}'")

            if requirement.get("verified_only") is True:
                filters.append("is_verified = true")

            if requirement.get("interview_marked") is True:
                filters.append("interview_marked = true")

            if requirement.get("fresher") is True:
                filters.append("fresher = true")
            elif requirement.get("fresher") is False or self._experience_minimum(requirement) is not None:
                filters.append("fresher = false")

        where_clause = "\nWHERE " + "\nAND ".join(filters) if filters else ""
        return f"SELECT {RECRUITER_COLUMNS}\nFROM resumes{where_clause};"

    def _unique_skills(self, requirement: dict[str, Any]) -> list[str]:
        skills: list[str] = []
        seen: set[str] = set()
        for field in SKILL_FIELDS:
            for skill in self._list(requirement.get(field)):
                key = skill.lower()
                if key in seen:
                    continue
                seen.add(key)
                skills.append(skill)
        return skills

    def _skill_filter(self, requirement: dict[str, Any], skill: str) -> str:
        aliases = self._skill_aliases(requirement, skill)
        filters = [
            f"skills::text ILIKE '%{self._escape_like(alias)}%'"
            for alias in aliases
        ]
        return "(" + " OR ".join(filters) + ")" if len(filters) > 1 else filters[0]

    @staticmethod
    def _skill_aliases(requirement: dict[str, Any], skill: str) -> list[str]:
        expanded = requirement.get("expanded_skills")
        if isinstance(expanded, dict):
            aliases = expanded.get(skill)
            if isinstance(aliases, list):
                values = [skill, *[str(alias) for alias in aliases]]
                result = []
                seen = set()
                for value in values:
                    clean = str(value or "").strip()
                    key = clean.lower()
                    if clean and key not in seen:
                        seen.add(key)
                        result.append(clean)
                return result
        return [skill]

    def _set_skill_fields(self, requirement: dict[str, Any], skills: list[str]) -> dict[str, Any]:
        for field in SKILL_FIELDS:
            requirement[field] = []
        requirement["mandatory_skills"] = skills
        return requirement

    @staticmethod
    def _experience_minimum(requirement: dict[str, Any]) -> int | None:
        experience = requirement.get("experience")
        if isinstance(experience, dict):
            return experience.get("minimum_years")
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
