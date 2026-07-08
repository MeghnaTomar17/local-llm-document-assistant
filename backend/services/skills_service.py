from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


logger = logging.getLogger(__name__)

DEFAULT_SKILLS_DICTIONARY_PATH = Path("backend/config/skills_dictionary.json")
SKILLS_DICTIONARY_PATH = Path(
    os.getenv("SKILLS_DICTIONARY_PATH", str(DEFAULT_SKILLS_DICTIONARY_PATH))
)
DEFAULT_GIS_DICTIONARY_PATH = Path("backend/config/gis_skills_dictionary.json")

SOFT_OR_NON_COMPETENCY_PATTERNS = (
    r"\bcommunication skills?\b",
    r"\bleadership\b",
    r"\bteam\s+player\b",
    r"\bteamwork\b",
    r"\bproblem\s+solving\b",
    r"\bself[-\s]?motivated\b",
    r"\bquick\s+learner\b",
    r"\bfast\s+learner\b",
    r"\bhard\s+working\b",
    r"\bpunctual\b",
    r"\bpositive\s+attitude\b",
    r"\benglish\b",
    r"\btamil\b",
    r"\bhindi\b",
    r"\bbengali\b",
    r"\bmarathi\b",
    r"\bnationality\b",
    r"\bdate\s+of\s+birth\b",
    r"\baddress\b",
    r"\bemail\b",
    r"\bphone\b",
    r"\bcgpa\b",
    r"\bgpa\b",
    r"\bmarks?\b",
    r"\bpercentage\b",
)


@dataclass(frozen=True)
class SkillEntry:
    canonical: str
    aliases: tuple[str, ...]


@lru_cache(maxsize=4)
def load_gis_dictionary(path: str | None = None) -> tuple[SkillEntry, ...]:
    dictionary_path = Path(path) if path else DEFAULT_GIS_DICTIONARY_PATH
    if not dictionary_path.exists():
        logger.warning("GIS skills dictionary not found: %s", dictionary_path)
        return tuple()
    try:
        return parse_json_dictionary(dictionary_path)
    except Exception as exc:
        logger.warning("Failed to load GIS skills dictionary %s: %s", dictionary_path, exc)
        return tuple()


def extract_dedicated_skills_sections(text: str) -> str:
    lines = text.splitlines()
    skills_text = []
    in_skills_section = False
    
    header_pattern = re.compile(
        r"^\s*(?:gis\s+skills|technical\s+skills|skills|technologies|software|key\s+skills|core\s+competencies|expertise|tools)\s*[:\-\u2013\u2014]*\s*$",
        re.IGNORECASE
    )
    stop_pattern = re.compile(
        r"^\s*(?:education|experience|work\s+history|employment|projects?|publications?|certifications?|awards?|languages|interests|hobbies|summary|about\s+me)\s*[:\-\u2013\u2014]*\s*$",
        re.IGNORECASE
    )
    
    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue
        if header_pattern.match(clean_line):
            in_skills_section = True
            continue
        if stop_pattern.match(clean_line):
            in_skills_section = False
            continue
        if in_skills_section:
            skills_text.append(clean_line)
            
    return "\n".join(skills_text)


def scan_gis_skills(text: str, gis_entries: tuple[SkillEntry, ...]) -> list[str]:
    alias_to_canonical = {}
    for entry in gis_entries:
        for alias in entry.aliases:
            alias_to_canonical[alias.lower()] = entry.canonical
            
    if not alias_to_canonical:
        return []
        
    sorted_aliases = sorted(alias_to_canonical.keys(), key=len, reverse=True)
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(alias) for alias in sorted_aliases) + r")\b",
        re.IGNORECASE
    )
    
    matches = pattern.findall(text)
    matched_skills = []
    seen = set()
    for m in matches:
        canonical = alias_to_canonical.get(m.lower())
        if canonical and canonical.lower() not in seen:
            matched_skills.append(canonical)
            seen.add(canonical.lower())
            
    return matched_skills


def get_canonical_gis(skill: str, gis_entries: tuple[SkillEntry, ...]) -> str:
    key = normalize_skill_key(skill)
    for entry in gis_entries:
        if key == normalize_skill_key(entry.canonical):
            return entry.canonical
        if any(key == normalize_skill_key(alias) for alias in entry.aliases):
            return entry.canonical
    return ""


def enhance_skills(llm_skills: Iterable[object], resume_text: str) -> list[str]:
    """Merge LLM skills with GIS skill validation layer and general skill dictionary matches."""
    gis_entries = load_gis_dictionary()
    general_entries = load_skill_dictionary()
    
    enhanced: list[str] = []
    seen: set[str] = set()

    def add(skill: str):
        if not is_professional_skill(skill):
            return
        key = normalize_skill_key(skill)
        if key and key not in seen:
            cased_skill = skill
            canonical_gis = get_canonical_gis(skill, gis_entries)
            if canonical_gis:
                cased_skill = canonical_gis
            else:
                canonical_gen = canonical_for_skill(skill, general_entries)
                if canonical_gen:
                    cased_skill = canonical_gen
            enhanced.append(cased_skill)
            seen.add(key)

    # 1. Prioritize GIS skills in dedicated sections
    skills_section_text = extract_dedicated_skills_sections(resume_text)
    section_gis_skills = scan_gis_skills(skills_section_text, gis_entries)
    for skill in section_gis_skills:
        add(skill)

    # 2. Scan full text for any additional GIS skills
    all_gis_skills = scan_gis_skills(resume_text, gis_entries)
    for skill in all_gis_skills:
        add(skill)

    # 3. Process LLM-extracted skills
    normalized_full_text = normalize_text_for_matching(resume_text)
    for skill in llm_skills or []:
        candidate = str(skill or "").strip()
        if not candidate:
            continue

        canonical_gis = get_canonical_gis(candidate, gis_entries)
        if canonical_gis:
            add(canonical_gis)
            continue

        canonical_gen = canonical_for_skill(candidate, general_entries)
        if canonical_gen:
            if skill_present_in_text(canonical_gen, normalized_full_text, general_entries):
                add(canonical_gen)
            continue

        if raw_skill_present_in_text(candidate, normalized_full_text):
            add(candidate)

    # 4. Fallback to general skill dictionary scan
    for entry in general_entries:
        if skill_present_in_text(entry.canonical, normalized_full_text, general_entries):
            add(entry.canonical)

    return enhanced


@lru_cache(maxsize=4)
def load_skill_dictionary(path: str | None = None) -> tuple[SkillEntry, ...]:
    dictionary_path = Path(path) if path else SKILLS_DICTIONARY_PATH

    if not dictionary_path.exists():
        logger.warning("Skills dictionary not found: %s", dictionary_path)
        return tuple()

    try:
        if dictionary_path.suffix.lower() == ".json":
            return parse_json_dictionary(dictionary_path)
        if dictionary_path.suffix.lower() in {".txt", ".text"}:
            return parse_txt_dictionary(dictionary_path)
        if dictionary_path.suffix.lower() in {".yaml", ".yml"}:
            return parse_simple_yaml_dictionary(dictionary_path)
    except Exception as exc:
        logger.warning("Failed to load skills dictionary %s: %s", dictionary_path, exc)
        return tuple()

    logger.warning("Unsupported skills dictionary format: %s", dictionary_path)
    return tuple()


def parse_json_dictionary(path: Path) -> tuple[SkillEntry, ...]:
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_skills = []
    
    if isinstance(data, dict):
        if "categories" in data:
            for cat_skills in data["categories"].values():
                if isinstance(cat_skills, list):
                    raw_skills.extend(cat_skills)
        elif "skills" in data:
            raw_skills = data["skills"]
        else:
            # Fallback if it has another dict key mapping to a list
            for val in data.values():
                if isinstance(val, list):
                    raw_skills.extend(val)
    else:
        raw_skills = data

    entries = []
    for item in raw_skills or []:
        if isinstance(item, str):
            entries.append(SkillEntry(item.strip(), (item.strip(),)))
            continue
        if isinstance(item, dict):
            canonical = str(item.get("name") or item.get("skill") or "").strip()
            aliases = item.get("aliases") or []
            if canonical:
                entries.append(SkillEntry(canonical, tuple(dict.fromkeys([canonical, *map(str, aliases)]))))

    return tuple(entries)


def parse_txt_dictionary(path: Path) -> tuple[SkillEntry, ...]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in re.split(r"\s*[|,]\s*", line) if part.strip()]
        if parts:
            entries.append(SkillEntry(parts[0], tuple(dict.fromkeys(parts))))
    return tuple(entries)


def parse_simple_yaml_dictionary(path: Path) -> tuple[SkillEntry, ...]:
    """Small YAML fallback for `- name:` / `aliases:` dictionaries without PyYAML."""

    entries = []
    current_name = ""
    current_aliases: list[str] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- name:"):
            if current_name:
                entries.append(SkillEntry(current_name, tuple(dict.fromkeys([current_name, *current_aliases]))))
            current_name = stripped.split(":", 1)[1].strip().strip("'\"")
            current_aliases = []
        elif stripped.startswith("aliases:"):
            raw_aliases = stripped.split(":", 1)[1].strip().strip("[]")
            current_aliases = [item.strip().strip("'\"") for item in raw_aliases.split(",") if item.strip()]

    if current_name:
        entries.append(SkillEntry(current_name, tuple(dict.fromkeys([current_name, *current_aliases]))))

    return tuple(entries)


def canonical_for_skill(skill: str, entries: tuple[SkillEntry, ...]) -> str:
    key = normalize_skill_key(skill)
    for entry in entries:
        if key == normalize_skill_key(entry.canonical):
            return entry.canonical
        if any(key == normalize_skill_key(alias) for alias in entry.aliases):
            return entry.canonical
    return ""


def normalize_skill_casing(skill: str, entries: tuple[SkillEntry, ...]) -> str:
    canonical = canonical_for_skill(skill, entries)
    if canonical:
        return canonical
    return re.sub(r"\s+", " ", skill).strip()


def skill_present_in_text(canonical: str, normalized_text: str, entries: tuple[SkillEntry, ...]) -> bool:
    entry = next((item for item in entries if normalize_skill_key(item.canonical) == normalize_skill_key(canonical)), None)
    aliases = entry.aliases if entry else (canonical,)
    return any(raw_skill_present_in_text(alias, normalized_text) for alias in aliases)


def raw_skill_present_in_text(skill: str, normalized_text: str) -> bool:
    skill = str(skill or "").strip()
    if not skill:
        return False

    normalized_skill = normalize_text_for_matching(skill)

    searchable_text = normalized_text
    if normalize_skill_key(skill) == "sql":
        searchable_text = re.sub(r"\b(?:postgre|my|sq|pl)\s*sql\b", " ", searchable_text)

    if re.fullmatch(r"[a-z0-9+#.]{1,4}", normalized_skill):
        return bool(re.search(rf"(?<![a-z0-9+#.]){re.escape(normalized_skill)}(?![a-z0-9+#.])", searchable_text))

    flexible = re.escape(normalized_skill).replace(r"\ ", r"[\s._/-]+")
    return bool(re.search(rf"(?<![a-z0-9+#.]){flexible}(?![a-z0-9+#.])", searchable_text))


def normalize_text_for_matching(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("\u00a0", " ")
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"(?<=[a-z])\s+(?=[a-z]\b)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_skill_key(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", "", str(value or "").lower())


def is_professional_skill(skill: str) -> bool:
    value = re.sub(r"\s+", " ", str(skill or "")).strip()
    if len(value) < 1 or len(value) > 80:
        return False
    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in SOFT_OR_NON_COMPETENCY_PATTERNS):
        return False
    if re.fullmatch(r"[\d.\-/ ]+", value):
        return False
    return True
