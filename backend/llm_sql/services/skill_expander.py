from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

from backend.services.skills_service import (
    SkillEntry,
    canonical_for_skill,
    load_gis_dictionary,
    load_skill_dictionary,
    normalize_skill_key,
)


SKILL_FIELDS = (
    "mandatory_skills",
    "preferred_skills",
    "gis_skills",
    "programming_languages",
    "frameworks",
    "databases",
    "cloud",
    "tools",
)

GENERIC_SKILL_TERMS = {
    "programming",
    "development",
    "software",
    "technology",
    "technologies",
    "project",
    "projects",
    "research",
    "teamwork",
    "communication",
    "good communication",
    "communication skills",
    "soft skills",
    "leadership",
    "ms office",
    "microsoft office",
    "microsoft word",
    "word",
    "powerpoint",
    "microsoft powerpoint",
}


@dataclass(frozen=True)
class ExpandedSkill:
    canonical: str
    aliases: tuple[str, ...]
    is_gis: bool = False


@lru_cache(maxsize=1)
def dictionary_entries() -> tuple[tuple[SkillEntry, ...], tuple[SkillEntry, ...]]:
    return load_gis_dictionary(), load_skill_dictionary()


class SkillExpander:
    """Normalize and expand search skills using configured dictionaries."""

    def normalize_skill(self, skill: str) -> str:
        value = str(skill or "").strip()
        if not value:
            return ""

        val_lower = value.lower()
        if val_lower in ("gp service", "gp services"):
            return "Geoprocessing"
        if val_lower in ("server manager", "server managers"):
            return "ArcGIS Server"

        gis_entries, general_entries = dictionary_entries()
        all_entries = list(gis_entries) + list(general_entries)

        canonical = self.find_canonical_skill(value, all_entries)
        if canonical:
            return canonical

        # Preserve clean unknown terms as exact canonical values. This keeps
        # explicitly requested acronyms and proprietary technologies searchable
        # without inventing aliases, while generic language remains excluded.
        return value if self._is_unknown_skill_candidate(value) else ""

    def split_combined_skills(self, phrase: str) -> list[str]:
        p = phrase
        p = re.sub(r"\s*&\s*", ",", p)
        p = re.sub(r"\s*\band\b\s*", ",", p, flags=re.IGNORECASE)
        p = re.sub(r"\s*\bor\b\s*", ",", p, flags=re.IGNORECASE)
        p = p.replace("/", ",").replace("\\", ",")
        p = re.sub(r"\s*\+\s*", ",", p)

        parts = [part.strip() for part in p.split(",") if part.strip()]
        return parts

    def find_canonical_skill(self, sub_phrase: str, all_entries: list[SkillEntry]) -> str | None:
        sub_clean = " " + re.sub(r"[^a-z0-9+#]+", " ", sub_phrase.lower()).strip() + " "

        match_candidates = []
        for entry in all_entries:
            canonical_clean = re.sub(r"[^a-z0-9+#]+", " ", entry.canonical.lower()).strip()
            if canonical_clean:
                match_candidates.append((canonical_clean, entry.canonical))
            for alias in entry.aliases:
                alias_clean = re.sub(r"[^a-z0-9+#]+", " ", alias.lower()).strip()
                if alias_clean:
                    match_candidates.append((alias_clean, entry.canonical))

        seen_candidates = set()
        deduped_candidates = []
        for term, canonical in match_candidates:
            key = (term, canonical)
            if key not in seen_candidates:
                seen_candidates.add(key)
                deduped_candidates.append(key)

        deduped_candidates.sort(key=lambda x: len(x[0]), reverse=True)

        for term_clean, canonical in deduped_candidates:
            if f" {term_clean} " in sub_clean:
                return canonical

        return None

    def normalize_and_split_skill(self, skill: str) -> list[str]:
        value = str(skill or "").strip()
        if not value:
            return []

        val_lower = value.lower()
        if val_lower == "arcgis enterprise framework":
            return ["ArcGIS Enterprise", "ArcGIS"]

        parts = self.split_combined_skills(value)
        gis_entries, general_entries = dictionary_entries()
        all_entries = list(gis_entries) + list(general_entries)

        canonical_skills = []
        for part in parts:
            canonical = self.normalize_skill(part)
            if canonical:
                canonical_skills.append(canonical)
            else:
                logger.info("Discarding non-canonical skill or workflow phrase: '%s'", part)

        return sorted(list(set(canonical_skills)))

    def expand_skill(self, skill: str) -> ExpandedSkill | None:
        canonical = self.normalize_skill(skill)
        if not canonical:
            return None

        gis_entries, general_entries = dictionary_entries()
        gis_entry = self._entry_for(canonical, gis_entries)
        if gis_entry:
            return ExpandedSkill(canonical=gis_entry.canonical, aliases=gis_entry.aliases, is_gis=True)

        general_entry = self._entry_for(canonical, general_entries)
        if general_entry:
            return ExpandedSkill(canonical=general_entry.canonical, aliases=general_entry.aliases, is_gis=False)

        return ExpandedSkill(canonical=canonical, aliases=(canonical,), is_gis=False)

    def expand_requirement(self, requirement: dict[str, Any]) -> dict[str, Any]:
        expanded = dict(requirement or {})
        expanded_map: dict[str, list[str]] = {}
        canonical_gis: list[str] = []

        for field in SKILL_FIELDS:
            normalized_values: list[str] = []
            for skill in self._list(expanded.get(field)):
                expanded_skill = self.expand_skill(skill)
                if not expanded_skill:
                    continue
                normalized_values.append(expanded_skill.canonical)
                expanded_map[expanded_skill.canonical] = self._unique(expanded_skill.aliases)
                if expanded_skill.is_gis and field != "preferred_skills":
                    canonical_gis.append(expanded_skill.canonical)
            expanded[field] = self._unique(normalized_values)

        if canonical_gis:
            expanded["gis_skills"] = self._unique([*self._list(expanded.get("gis_skills")), *canonical_gis])

        expanded["expanded_skills"] = expanded_map
        return expanded

    def add_explicit_skills(self, requirement: dict[str, Any], skills: list[str]) -> dict[str, Any]:
        """Merge explicit recruiter terms, self-mapping terms unknown to the dictionaries."""
        expanded = dict(requirement or {})
        expanded_map = dict(expanded.get("expanded_skills") or {})
        mandatory_skills = self._list(expanded.get("mandatory_skills"))
        canonical_gis = self._list(expanded.get("gis_skills"))

        for skill in skills:
            clean = " ".join(str(skill or "").split())
            if not clean:
                continue
            expanded_skill = self.expand_skill(clean) or ExpandedSkill(clean, (clean,))
            mandatory_skills.append(expanded_skill.canonical)
            expanded_map[expanded_skill.canonical] = self._unique(expanded_skill.aliases)
            if expanded_skill.is_gis:
                canonical_gis.append(expanded_skill.canonical)

        expanded["mandatory_skills"] = self._unique(mandatory_skills)
        expanded["gis_skills"] = self._unique(canonical_gis)
        expanded["expanded_skills"] = expanded_map
        return expanded

    def normalize_requirement_skill_phrases(self, requirement: dict[str, Any]) -> dict[str, Any]:
        """Remove only trailing recruiter intent words before rebuilding expansions."""
        normalized = dict(requirement or {})
        for field in SKILL_FIELDS:
            normalized[field] = self._unique(
                [self._strip_skill_intent(skill) for skill in self._list(normalized.get(field))]
            )
        return self.expand_requirement(normalized)

    def is_gis_skill(self, skill: str) -> bool:
        expanded = self.expand_skill(skill)
        return bool(expanded and expanded.is_gis)

    @staticmethod
    def _entry_for(skill: str, entries: tuple[SkillEntry, ...]) -> SkillEntry | None:
        key = normalize_skill_key(skill)
        for entry in entries:
            if key == normalize_skill_key(entry.canonical):
                return entry
            if any(key == normalize_skill_key(alias) for alias in entry.aliases):
                return entry
        return None

    @staticmethod
    def _list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _unique(values: tuple[str, ...] | list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            clean = " ".join(str(value or "").split())
            key = clean.lower()
            if not clean or key in seen:
                continue
            seen.add(key)
            result.append(clean)
        return result

    @staticmethod
    def _candidate_normalization_forms(value: str) -> list[str]:
        clean = " ".join(str(value or "").split())
        forms = [clean]
        lower = clean.lower()

        for suffix in (" programming", " development", " basics", " basic"):
            if lower.endswith(suffix):
                forms.append(clean[: -len(suffix)].strip())

        for prefix in ("basics of ", "basic of ", "knowledge of ", "experience in ", "hands on "):
            if lower.startswith(prefix):
                forms.append(clean[len(prefix):].strip())

        return [form for form in forms if form]

    @staticmethod
    def _is_generic(value: str) -> bool:
        key = " ".join(str(value or "").strip().lower().split())
        return key in GENERIC_SKILL_TERMS

    @classmethod
    def _is_unknown_skill_candidate(cls, value: str) -> bool:
        clean = " ".join(str(value or "").split())
        if not clean or len(clean) > 80 or len(clean.split()) > 5:
            return False
        if cls._is_generic(clean):
            return False
        return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .+#/_-]*", clean))

    @staticmethod
    def _strip_skill_intent(value: str) -> str:
        return re.sub(r"\s+skills?\s*$", "", str(value or ""), flags=re.IGNORECASE).strip()
