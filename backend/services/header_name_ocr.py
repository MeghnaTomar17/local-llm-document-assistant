"""Targeted first-page header OCR for missing resume candidate names."""

from __future__ import annotations

from functools import lru_cache
import logging
import re
from pathlib import Path


logger = logging.getLogger(__name__)

_NON_NAME_VALUES = {
    "resume", "curriculum vitae", "cv", "certificate", "certification",
    "profile", "professional profile", "summary", "professional summary",
    "objective", "career objective", "experience", "work experience",
    "education", "skills", "technical skills", "projects", "achievements",
    "contact", "contact details", "personal details", "declaration",
    "references", "music nature",
}
_NON_NAME_TERMS = {
    "developer", "engineer", "analyst", "designer", "illustrator", "architect", "manager",
    "consultant", "intern", "trainee", "specialist", "administrator",
    "certificate", "certification", "professional", "student", "fresher",
}


def is_valid_candidate_name(value: object) -> bool:
    """Return whether a value is safe to persist as a candidate name."""
    name = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;|-")
    if not name or len(name) > 60:
        return False
    if "@" in name or re.search(r"https?://|www\.", name, flags=re.IGNORECASE):
        return False

    words = name.split()
    if not 1 <= len(words) <= 5 or any(char.isdigit() for char in name):
        return False
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
        return False

    lowered = name.lower()
    if lowered in _NON_NAME_VALUES:
        return False
    if any(term in lowered.split() for term in _NON_NAME_TERMS):
        return False
    return True


def _normalise_candidate(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" .,:;|-")
    return value.title() if value.isupper() or value.islower() else value


def extract_name_from_header(header_text: str) -> str:
    """Select a validated, name-like line from small header-only OCR output."""
    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in str(header_text or "").splitlines()
    ]
    scored_candidates: list[tuple[int, str]] = []

    for index, line in enumerate(line for line in lines if line):
        # OCR can join contact details to a name; retain only the text before them.
        segments = re.split(r"[|\u2022]", line)
        for segment in segments:
            candidate = re.sub(
                r"^(?:name|candidate name|full name)\s*[:\-]\s*",
                "",
                segment,
                flags=re.IGNORECASE,
            ).strip()
            candidate = re.split(r"\s+(?:\S+@\S+|\+?\d[\d\s().-]{8,})", candidate)[0]
            candidate = _normalise_candidate(candidate)
            if not is_valid_candidate_name(candidate):
                continue

            words = candidate.split()
            score = max(0, 30 - index * 3)
            if 2 <= len(words) <= 4:
                score += 12
            if any(re.fullmatch(r"[A-Z]\.", word) for word in words):
                score += 8
            if candidate == candidate.title():
                score += 3
            scored_candidates.append((score, candidate))

    if not scored_candidates:
        return ""
    return max(scored_candidates, key=lambda item: item[0])[1]


@lru_cache(maxsize=1)
def get_easyocr_reader():
    import easyocr

    return easyocr.Reader(["en"], gpu=False)


def extract_header_text_for_name(file_path: str | Path) -> str:
    """OCR only the upper 35% of page 1, returning text for name recovery."""
    try:
        import fitz
        import numpy as np
        from PIL import Image

        path = Path(file_path)
        if path.suffix.lower() != ".pdf":
            return ""

        with fitz.open(path) as document:
            if document.page_count < 1:
                logger.warning("Header OCR skipped because no first page was available: %s", path.name)
                return ""
            page = document[0]
            header_rect = fitz.Rect(page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y0 + page.rect.height * 0.35)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2.8, 2.8), clip=header_rect, alpha=False)

        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        lines = get_easyocr_reader().readtext(np.array(image), detail=0, paragraph=False)
        return "\n".join(str(line).strip() for line in lines if str(line).strip())
    except Exception as exc:
        logger.warning("Targeted header OCR failed for %s: %s", Path(file_path).name, exc)
        return ""
