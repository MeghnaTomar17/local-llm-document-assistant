"""Recover explicitly requested technical terms missed by requirement extraction."""

from __future__ import annotations

import re


_EXPLICIT_SKILL_PATTERNS = (
    r"\b(?:people|candidates|applicants|developers)\s+with\s+(?P<term>[^.\n;:]+?)\s+skills?\b",
    r"\b(?:people|candidates|applicants|developers)\s+(?:skilled|experienced|proficient|familiar)\s+(?:in|with)\s+(?P<term>[^.\n;:]+)",
    r"\b(?:skilled|experienced|proficient|familiar)\s+(?:in|with)\s+(?P<term>[^.\n;:]+)",
    r"\bexperience\s+with\s+(?P<term>[^.\n;:]+)",
    r"\bknowledge\s+of\s+(?P<term>[^.\n;:]+)",
    r"\b(?:candidates\s+who\s+know|looking\s+for\s+candidates\s+who\s+know)\s+(?P<term>[^.\n;:]+)",
)
_ORDINARY_LANGUAGE_TERMS = {
    "communication", "good communication", "communication skills", "soft skills",
    "teamwork", "leadership", "problem solving", "hard working", "all candidates",
}


def recover_explicit_skills(query: str) -> list[str]:
    """Return skill candidates only when recruiter phrasing explicitly signals skill intent."""
    recovered: list[str] = []
    seen: set[str] = set()

    for pattern in _EXPLICIT_SKILL_PATTERNS:
        for match in re.finditer(pattern, str(query or ""), flags=re.IGNORECASE):
            for term in _split_terms(match.group("term")):
                key = term.lower()
                if key not in seen and _is_skill_candidate(term):
                    seen.add(key)
                    recovered.append(term)
    return recovered


def _split_terms(value: str) -> list[str]:
    clean = re.sub(r"\s+", " ", str(value or "")).strip(" ,.;:-")
    clean = re.sub(r"^(?:the|a|an)\s+", "", clean, flags=re.IGNORECASE)
    return [part.strip(" ,.;:-") for part in re.split(r"\s*(?:,|/|&|\band\b)\s*", clean, flags=re.IGNORECASE) if part.strip(" ,.;:-")]


def _is_skill_candidate(value: str) -> bool:
    clean = re.sub(r"\s+", " ", str(value or "")).strip(" ,.;:-")
    if not clean or len(clean) > 80 or len(clean.split()) > 5:
        return False
    if clean.lower() in _ORDINARY_LANGUAGE_TERMS:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .+#/_-]*", clean))
