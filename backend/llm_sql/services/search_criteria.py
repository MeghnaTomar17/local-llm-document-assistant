"""Deterministic checks for requirement fields the SQL builder can filter."""

from __future__ import annotations

from typing import Any

from backend.llm_sql.services.sql_builder import ALL_SKILL_FIELDS


def has_searchable_criteria(requirement: dict[str, Any] | None) -> bool:
    """Return whether validated requirement data will add a SQL search filter."""
    data = requirement or {}
    if any(_has_value(data.get(field)) for field in ALL_SKILL_FIELDS):
        return True
    if _has_value(data.get("cities") or data.get("locations")):
        return True
    if str(data.get("candidate_type") or "").strip().upper() in {"INTERNAL", "EXTERNAL"}:
        return True
    if data.get("verified_only") is True or data.get("interview_marked") is True:
        return True
    if data.get("fresher") is not None:
        return True

    experience = data.get("experience")
    if isinstance(experience, dict):
        return experience.get("minimum_years") is not None or experience.get("minimum") is not None
    return isinstance(experience, int) and not isinstance(experience, bool)


def _has_value(value: Any) -> bool:
    if isinstance(value, list):
        return any(str(item).strip() for item in value)
    return bool(str(value or "").strip())
