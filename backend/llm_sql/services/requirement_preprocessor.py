from __future__ import annotations

import os
import re

MAX_PROMPT_CHARS_DEFAULT = 4000

# Mapping of section names to lists of regex patterns
SECTION_PATTERNS = {
    "required_skills": [
        r"required\s+skills?",
        r"technical\s+skills?",
        r"must[- ]have\s+skills?",
        r"skills\s+required",
        r"skills\s+and\s+technologies",
        r"technology\s+stack",
    ],
    "qualifications": [
        r"required\s+qualifications?",
        r"minimum\s+qualifications?",
        r"mandatory\s+qualifications?",
        r"qualifications?",
        r"education",
    ],
    "experience": [
        r"experience\s+requirements?",
        r"experience",
        r"work\s+experience",
        r"professional\s+experience",
    ],
    "responsibilities": [
        r"responsibilities",
        r"key\s+responsibilities",
        r"what\s+you\s+will\s+do",
        r"role\s+responsibilities?",
        r"job\s+duties",
        r"duties",
    ],
    "preferred_skills": [
        r"preferred\s+skills?",
        r"nice[- ]to[- ]have\s+skills?",
        r"good[- ]to[- ]have\s+skills?",
        r"desired\s+skills?",
        r"preferred\s+qualifications?",
    ],
    "certifications": [
        r"certifications?",
        r"licenses?",
        r"credentials?",
    ],
    # Non-hiring sections to discard
    "discard": [
        r"about\s+us",
        r"who\s+we\s+are",
        r"company\s+overview",
        r"our\s+mission",
        r"benefits",
        r"perks",
        r"compensation",
        r"benefits\s+and\s+perks",
        r"equal\s+opportunity",
        r"diversity",
        r"eeo",
        r"employment\s+opportunity",
    ]
}


def preprocess_requirement(text: str, max_chars: int | None = None) -> str:
    """Preprocess recruiter requirements/JDs to strip bullets, non-hiring blocks,

    and prioritize relevant sections under a configurable character limit.
    """
    if max_chars is None:
        try:
            max_chars = int(os.getenv("MAX_PROMPT_CHARS", str(MAX_PROMPT_CHARS_DEFAULT)))
        except ValueError:
            max_chars = MAX_PROMPT_CHARS_DEFAULT

    if not text:
        return ""

    # 1. Normalize line endings and double line breaks for paragraph boundaries
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Normalize smart punctuation to straight quotes
    text = re.sub(r"[\u201c\u201d\u201e\u201f\u2033\u2036]", '"', text)
    text = re.sub(r"[\u2018\u2019\u201a\u201b\u2032\u2035]", "'", text)

    # 3. Clean line by line (remove list bullets, numberings, markdown bold/italic)
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # Remove lines consisting only of dashes, equals, or underscores (e.g. underlines)
        if re.match(r"^[-=_\s]+$", line):
            continue

        # Remove markdown bold/italic/strikethrough
        line = re.sub(r"(\*\*|__|\*|_|~~)", "", line)

        # Remove list bullet and numbering prefixes (e.g. "- ", "* ", "1. ", "a) ")
        line = re.sub(r"^(\s*[-*+•]\s+)|(\s*\d+[\.)-]\s+)|(\s*[a-zA-Z][\.)]\s+)", "", line)
        cleaned_lines.append(line.strip())

    # Reassemble line-cleaned text
    text = "\n".join(cleaned_lines)

    # Split into paragraphs (delimited by multiple newlines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    # Classify paragraphs into sections
    sections: dict[str, list[str]] = {
        "required_skills": [],
        "qualifications": [],
        "experience": [],
        "responsibilities": [],
        "preferred_skills": [],
        "certifications": [],
        "other": []
    }

    current_section = "other"

    for paragraph in paragraphs:
        # Check first line of paragraph to see if it matches a section header
        first_line = paragraph.split("\n")[0].strip().lower()
        # Clean header name (remove colon, trailing dashes/equals, spaces)
        first_line_clean = re.sub(r"[:\-\s\=]+$", "", first_line).strip()

        matched_section = None
        # Check discard list first
        for pattern in SECTION_PATTERNS["discard"]:
            if re.match(r"^" + pattern + r"$", first_line_clean) or re.match(r"^\b" + pattern + r"\b", first_line_clean):
                matched_section = "discard"
                break

        if not matched_section:
            for sec_name, patterns in SECTION_PATTERNS.items():
                if sec_name == "discard":
                    continue
                for pattern in patterns:
                    if re.match(r"^" + pattern + r"$", first_line_clean) or re.match(r"^\b" + pattern + r"\b", first_line_clean):
                        matched_section = sec_name
                        break
                if matched_section:
                    break

        if matched_section:
            current_section = matched_section
            # Strip the header line itself to keep the prompt clean
            header_lines = paragraph.split("\n")
            if len(header_lines) > 1:
                paragraph_content = "\n".join(header_lines[1:]).strip()
                if paragraph_content and current_section != "discard":
                    sections[current_section].append(paragraph_content)
            continue

        if current_section != "discard":
            sections[current_section].append(paragraph)

    # Priority order to assemble prompt
    priority_order = [
        "required_skills",
        "qualifications",
        "experience",
        "responsibilities",
        "preferred_skills",
        "certifications",
        "other"
    ]

    assembled_paragraphs = []
    current_length = 0

    for sec in priority_order:
        sec_paras = sections[sec]
        for para in sec_paras:
            para_len = len(para)
            if current_length + para_len + 2 > max_chars:
                remaining_budget = max_chars - current_length - 2
                if remaining_budget > 50:
                    truncated = para[:remaining_budget]
                    last_space = truncated.rfind(" ")
                    if last_space > 0:
                        truncated = truncated[:last_space]
                    assembled_paragraphs.append(truncated.strip() + "...")
                break
            assembled_paragraphs.append(para)
            current_length += para_len + 2
        else:
            continue
        break

    # Join with logical paragraph boundaries (double newlines)
    result = "\n\n".join(assembled_paragraphs)

    # Fallback if empty
    if not result.strip() and text.strip():
        result = text.strip()[:max_chars].strip()

    return result
