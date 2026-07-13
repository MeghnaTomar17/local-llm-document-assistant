from __future__ import annotations

import json
import logging
import re

from backend.llm_sql.services.skill_expander import SkillExpander

logger = logging.getLogger(__name__)


class RequirementValidationError(ValueError):
    """Raised when JSON validation fails permanently."""


class RequirementValidator:
    """Validate, clean, normalize, and enrich extracted structured recruiter requirements JSON."""

    def __init__(self, skill_expander: SkillExpander | None = None) -> None:
        self.skill_expander = skill_expander or SkillExpander()

    def normalize_skill(self, skill_name: str) -> str:
        return self.skill_expander.normalize_skill(skill_name)

    @staticmethod
    def _clean_list_value(value: str) -> str:
        value = re.sub(r"\s+", " ", str(value or "")).strip()
        return value.strip(" ,;:")

    def validate_and_clean(self, raw_json_str: str) -> dict:
        """Parse raw JSON string, repair minor issues, and apply normalization schemas."""
        cleaned_str = str(raw_json_str or "").strip()
        
        fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned_str, flags=re.IGNORECASE | re.DOTALL)
        if fenced_match:
            cleaned_str = fenced_match.group(1).strip()

        try:
            data = json.loads(cleaned_str)
        except json.JSONDecodeError as err:
            logger.error(
                "JSON decode error during requirement parsing: %s raw_chars=%d",
                err,
                len(cleaned_str),
            )
            raise RequirementValidationError(f"Invalid JSON format: {err}") from err

        if not isinstance(data, dict):
            raise RequirementValidationError("Decoded JSON is not a dictionary.")

        schema = {
            "role": data.get("role") or data.get("job_title") or data.get("title"),
            "experience": data.get("experience") if isinstance(data.get("experience"), dict) else {},
            "mandatory_skills": data.get("mandatory_skills") or data.get("required_skills"),
            "preferred_skills": data.get("preferred_skills"),
            "gis_skills": data.get("gis_skills"),
            "programming_languages": data.get("programming_languages"),
            "frameworks": data.get("frameworks"),
            "databases": data.get("databases"),
            "cloud": data.get("cloud"),
            "tools": data.get("tools"),
            "education": data.get("education"),
            "certifications": data.get("certifications"),
            "locations": data.get("location") or data.get("locations") or data.get("cities"),
            "industries": data.get("industries"),
            "candidate_type": data.get("candidate_type"),
            "fresher": data.get("fresher"),
            "verified_only": data.get("verified_only"),
            "interview_marked": data.get("interview_requirement") or data.get("interview_marked")
        }

        # 1. Clean Experience limits
        exp = schema["experience"]
        if not isinstance(exp, dict):
            exp = {}
        
        min_years = exp.get("minimum_years")
        max_years = exp.get("maximum_years")
        if min_years is None:
            min_years = exp.get("minimum")
        if max_years is None:
            max_years = exp.get("maximum")
        try:
            schema["experience"] = {
                "minimum_years": int(min_years) if min_years is not None and str(min_years).strip().isdigit() else None,
                "maximum_years": int(max_years) if max_years is not None and str(max_years).strip().isdigit() else None
            }
        except (ValueError, TypeError):
            schema["experience"] = {"minimum_years": None, "maximum_years": None}

        # 2. Clean and Normalize string list fields
        skill_list_fields = [
            "mandatory_skills", "preferred_skills", "gis_skills",
            "programming_languages", "frameworks", "databases", "cloud",
            "tools"
        ]
        plain_list_fields = [
            "education", "certifications", "locations", "industries"
        ]

        for field in skill_list_fields:
            raw_list = schema[field]
            if not isinstance(raw_list, list):
                if isinstance(raw_list, str):
                    raw_list = [raw_list]
                else:
                    raw_list = []

            cleaned_list = []
            for item in raw_list:
                cleaned_items = self.skill_expander.normalize_and_split_skill(str(item))
                cleaned_list.extend(cleaned_items)

            unique_list = sorted(list(set(cleaned_list)), key=lambda s: s.lower())
            schema[field] = unique_list

        for field in plain_list_fields:
            raw_list = schema[field]
            if not isinstance(raw_list, list):
                if isinstance(raw_list, str):
                    raw_list = [raw_list]
                else:
                    raw_list = []

            cleaned_list = []
            for item in raw_list:
                cleaned_item = self._clean_list_value(str(item))
                if cleaned_item:
                    cleaned_list.append(cleaned_item)

            unique_list = sorted(list(set(cleaned_list)), key=lambda s: s.lower())
            schema[field] = unique_list

        schema["education"] = [self._standardize_education(value) for value in schema["education"]]
        schema["locations"] = [self._standardize_city(value) for value in schema["locations"]]
        schema["cities"] = schema["locations"]

        # 3. Clean string / enum values
        role = schema["role"]
        role_text = str(role).strip() if role is not None else ""
        schema["role"] = role_text or None

        c_type = schema["candidate_type"]
        if c_type is not None:
            c_type_str = str(c_type).upper().strip()
            if c_type_str in ["INTERNAL", "EXTERNAL"]:
                schema["candidate_type"] = c_type_str
            else:
                schema["candidate_type"] = None
        else:
            schema["candidate_type"] = None

        # 4. Clean Booleans
        for bool_field in ["fresher", "verified_only", "interview_marked"]:
            val = schema[bool_field]
            if val is not None:
                if isinstance(val, bool):
                    schema[bool_field] = val
                elif str(val).lower() in ["true", "1", "yes"]:
                    schema[bool_field] = True
                elif str(val).lower() in ["false", "0", "no"]:
                    schema[bool_field] = False
                else:
                    schema[bool_field] = None
            else:
                schema[bool_field] = None

        return self.skill_expander.expand_requirement(schema)

    @staticmethod
    def _standardize_education(value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        key = re.sub(r"[^a-z0-9]", "", text.lower())
        aliases = {
            "btech": "B.Tech",
            "bacheloroftechnology": "B.Tech",
            "be": "BE",
            "bachelorofengineering": "BE",
            "mtech": "M.Tech",
            "masteroftechnology": "M.Tech",
            "mca": "MCA",
            "bca": "BCA",
            "msc": "M.Sc",
            "bsc": "B.Sc",
            "phd": "PhD",
        }
        return aliases.get(key, text)

    @staticmethod
    def _standardize_city(value: str) -> str:
        text = re.sub(r"\s+", " ", str(value or "").strip())
        aliases = {
            "bangalore": "Bengaluru",
            "bengaluru": "Bengaluru",
            "chennai": "Chennai",
            "delhi": "Delhi",
            "new delhi": "Delhi",
            "hyderabad": "Hyderabad",
            "mumbai": "Mumbai",
            "pune": "Pune",
            "kolkata": "Kolkata",
        }
        return aliases.get(text.lower(), text.title() if text.islower() else text)
