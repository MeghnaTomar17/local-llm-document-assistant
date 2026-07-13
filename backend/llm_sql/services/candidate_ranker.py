from __future__ import annotations

from typing import Any
from backend.llm_sql.services.skill_expander import SkillExpander

ALL_SKILL_FIELDS = (
    "mandatory_skills",
    "preferred_skills",
    "gis_skills",
    "programming_languages",
    "frameworks",
    "databases",
    "cloud",
    "tools",
)

class CandidateRanker:
    """Compare candidate skills against recruiter requirement skills without ranking or scoring."""

    def __init__(self, skill_expander: SkillExpander | None = None) -> None:
        self.skill_expander = skill_expander or SkillExpander()

    def rank(
        self,
        rows: list[dict[str, Any]],
        requirement: dict[str, Any] | None,
        candidate_type: str | None = None,
        order_cols: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        # Map match details for all rows in the exact SQL order
        matched_rows = [self.match_row(row, requirement or {}) for row in rows]
        
        # Filter out candidates with 0 matched skills to ensure high accuracy.
        # Only do this if some skills were actually requested in the search requirement.
        has_requested_skills = False
        if requirement:
            for field in ALL_SKILL_FIELDS:
                if requirement.get(field):
                    has_requested_skills = True
                    break
                    
        if has_requested_skills:
            matched_rows = [r for r in matched_rows if len(r.get("matched_skills", [])) > 0]
            
        return matched_rows

    def match_row(self, row: dict[str, Any], requirement: dict[str, Any]) -> dict[str, Any]:
        row_copy = dict(row)
        
        # Parse candidate skills
        row_skills, canonical_to_raw = self._canonical_skill_set_with_mapping(row_copy.get("skills"))
        
        # Collect required skills from all technical fields
        jd_skills = self._requirement_skills(requirement, ALL_SKILL_FIELDS)
        
        matched_skills: list[str] = []
        missing_skills: list[str] = []
        
        for skill in jd_skills:
            # Resolve aliases
            aliases = [skill]
            expanded = requirement.get("expanded_skills")
            if isinstance(expanded, dict) and isinstance(expanded.get(skill), list):
                aliases.extend(str(alias) for alias in expanded[skill])
                
            normalized_aliases = {
                self.skill_expander.normalize_skill(alias).lower()
                for alias in aliases
                if str(alias).strip()
            }
            
            matched_canon = normalized_aliases & row_skills
            if matched_canon:
                # Find raw candidate spelling
                for mc in matched_canon:
                    raw_spelling = canonical_to_raw.get(mc)
                    if raw_spelling and raw_spelling not in matched_skills:
                        matched_skills.append(raw_spelling)
            else:
                missing_skills.append(skill)
                
        row_copy["matched_skills"] = sorted(matched_skills, key=lambda s: s.lower())
        row_copy["missing_skills"] = sorted(missing_skills, key=lambda s: s.lower())
        row_copy["experience"] = "Fresher" if row_copy.get("fresher") else "Experienced"
        row_copy["phone"] = row_copy.get("phone_number")
        
        # Remove any old overall_match or candidate_score properties for safety
        row_copy["search_score"] = None
        row_copy["match_explanation"] = []
        row_copy["match_details"] = {}
        row_copy["normalized_candidate_skills"] = sorted(row_skills)
        
        return row_copy

    def _requirement_skills(self, requirement: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
        skills: list[str] = []
        seen: set[str] = set()
        for field in fields:
            for skill in self._list(requirement.get(field)):
                key = skill.lower()
                if key not in seen:
                    seen.add(key)
                    skills.append(skill)
        return skills

    def _canonical_skill_set_with_mapping(self, value: Any) -> tuple[set[str], dict[str, str]]:
        if isinstance(value, list):
            raw_values = [str(item).strip() for item in value if str(item).strip()]
        elif isinstance(value, str):
            raw_values = [item.strip() for item in value.split(",") if item.strip()]
        else:
            raw_values = []

        canonical: set[str] = set()
        canonical_to_raw: dict[str, str] = {}
        for item in raw_values:
            parts = self.skill_expander.split_combined_skills(item)
            for part in parts:
                normalized = self.skill_expander.normalize_skill(part)
                if normalized:
                    canonical.add(normalized.lower())
                    canonical_to_raw[normalized.lower()] = part
        return canonical, canonical_to_raw

    @staticmethod
    def _list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []
