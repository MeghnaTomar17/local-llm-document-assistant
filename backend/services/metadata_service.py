from os import name
from pathlib import Path
import csv
import logging
import re

from backend.services.llm_metadata_extractor import extract_metadata_with_ollama

logger = logging.getLogger(__name__)

METADATA_FIELDS = [
    "Resume File Name",
    "Candidate Name",
    "Email",
    "Phone Number",
]


class ResumeMetadataService:
    def __init__(self, output_dir=".", llm_model=None):
        self.output_dir = Path(output_dir)
        self.llm_model = llm_model
        self.records = []
        self.txt_path = self.output_dir / "metadata.txt"
        self.csv_path = self.output_dir / "metadata.csv"
        self.reset()

    def reset(self):
        self.records = []
        self.regenerate_files()

    def add_resume(self, file_name, extracted_text):
        record = extract_resume_metadata(file_name, extracted_text, llm_model=self.llm_model)
        self.add_record(record)
        return record

    def add_record(self, record):
        self.records.append(record)
        self.regenerate_files()
        return record

    def regenerate_files(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.write_txt()
        self.write_csv()

    def write_txt(self):
        lines = []
        for index, record in enumerate(self.records, start=1):
            lines.append(f"Resume {index}")
            for field in METADATA_FIELDS:
                lines.append(f"{field}: {record.get(field, '')}")
            lines.append("")

        self.txt_path.write_text("\n".join(lines), encoding="utf-8")

    def write_csv(self):
        with self.csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=METADATA_FIELDS)
            writer.writeheader()
            writer.writerows(self.records)


def extract_resume_metadata(file_name, extracted_text, llm_model=None):
    text = extracted_text or ""
    llm_metadata = extract_metadata_with_ollama(text, model=llm_model)
    print("\nLLM METADATA:")
    print(llm_metadata)

    logger.info("Validated LLM metadata for %s: %s", file_name, llm_metadata)
    fallback_metadata = None

    def fallback_value(field):
        nonlocal fallback_metadata
        if fallback_metadata is None:
            fallback_metadata = deterministic_metadata_fallback(file_name, text)
        return fallback_metadata[field]

    return {
        "Resume File Name": file_name or "",
        "Candidate Name": llm_metadata.get("candidate_name") or fallback_value("Candidate Name"),
        "Email": llm_metadata.get("email") or fallback_value("Email"),
        "Phone Number": (llm_metadata.get("phone_number") or fallback_value("Phone Number")),
    }


def deterministic_metadata_fallback(file_name, text):
    logger.info("Using deterministic metadata fallback for %s", file_name)

    candidate_name = extract_candidate_name(text)

    if not looks_like_person_name(candidate_name):
        candidate_name = extract_candidate_name_from_file_name(file_name)

    return {
        "Candidate Name": candidate_name,
        "Email": extract_email(text),
        "Phone Number": extract_phone_number(text),
    }


def extract_email(text):
    # Deterministic regex for standard email matching
    match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    return match.group(0) if match else ""


def extract_phone_number(text):
    phone_patterns = [
        r"\+?\d[\d\s().-]{8,}\d",
        r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}",
    ]

    # Only search the resume header
    header_text = "\n".join(text.splitlines()[:40])

    for pattern in phone_patterns:
        for match in re.finditer(pattern, header_text):

            candidate = normalize_phone(match.group(0))
            digits = re.sub(r"\D", "", candidate)

            # Reject years
            if re.match(r"^(19|20)\d{2}", digits):
                continue

            # Reject common year ranges
            if digits in {
                "20182022",
                "20232024",
                "20222024",
                "20192023",
                "20202024",
                "20212025",
            }:
                continue

            if is_plausible_phone(candidate):
                return candidate

    return ""


def normalize_phone(value):
    value = re.sub(
        r"\b(?:19|20)\d{2}\b.*$",
        "",
        str(value or "")
    ).strip()

    digits = re.sub(r"\D", "", value)

    # Indian number with country code
    if digits.startswith("91") and len(digits) == 12:
        return f"+91 {digits[2:]}"

    # Indian number with leading 0
    if digits.startswith("0") and len(digits) == 11:
        return digits

    # Standard 10-digit number
    if len(digits) == 10:
        return digits

    # International numbers
    if 11 <= len(digits) <= 15:
        return re.sub(r"\s+", " ", value).strip(" .-")

    return ""


def is_plausible_phone(value):
    digits = re.sub(r"\D", "", value)
    if not 10 <= len(digits) <= 15:
        return False
    if re.search(r"\b(19|20)\d{2}\b.*\b(19|20)\d{2}\b", value):
        return False
    if re.search(r"\b(?:cgpa|gpa|score|marks|percentage|percent|grade)\b", value, flags=re.IGNORECASE):
        return False
    return True


def extract_candidate_name(text):
    # Process only up to the first 50 meaningful, non-blank lines
    raw_lines = text.splitlines()[:50]
    lines = [clean_line(line) for line in raw_lines if clean_line(line)]

    # Strategy 1: Explicitly tagged fields take ultimate precedence
    for line in lines:
        m = re.match(
            r"^(?:name|candidate name|full name)\s*[:|-]\s*(.+)$",
            line,
            flags=re.IGNORECASE,
        )
        if m:
            candidate = clean_line(m.group(1))
            if looks_like_person_name(candidate):
                return title_case_name(candidate)

    # Strategy 2: Multi-factor scoring logic for unlabelled headers
    scored_candidates = []
    
    for index, line in enumerate(lines):
        if should_skip_name_line(line):
            continue
            
        candidate = strip_name_prefix(line)
        candidate = strip_name_prefix(candidate)

        candidate = re.sub(r"\b(senior|junior|lead|principal|intern|developer|engineer|analyst|manager|consultant)\b.*$","",candidate,flags=re.I,).strip()

        if looks_like_person_name(candidate):
            score = 0
            words = candidate.split()
            
            # Heuristic: Prioritize lines closest to the top of the resume
            score += max(0, (20 - index) * 2)

            if len(words) == 2:
                score += 20
            elif len(words) == 3:
                score += 15

            if candidate.isupper():
                score += 20

            if candidate == candidate.title():
                score += 5

            if any(re.match(r"^[A-Z]\.$", w) for w in words):
                score += 10

            if words[0][0].isupper():
                score += 5

            scored_candidates.append((score, candidate))

    if scored_candidates:
        # Sort by highest score descending and return the strongest candidate
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return title_case_name(scored_candidates[0][1])

    return ""


def extract_candidate_name_from_file_name(file_name):
    if not file_name:
        return ""

    stem = Path(file_name).stem
    stem = re.sub(r"[_\-]+", " ", stem)
    # Remove metadata boilerplate terms
    stem = re.sub(r"\b(?:resume|cv|curriculum|vitae|final|latest|updated|copy|new|ats)\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\b(?:pdf|docx|doc)\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\([^)]*\)", " ", stem)
    stem = re.sub(r"\d+", " ", stem)
    stem = re.sub(r"\s+", " ", stem)
    stem = stem.strip()
    stem = re.sub(r"\bfinal\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\bupdated\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\bcopy\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\bnew\b", " ", stem, flags=re.IGNORECASE)
    stem = clean_line(stem)
    stem = re.sub(r"\s+", " ", stem).strip()

    if looks_like_person_name(stem):
        return title_case_name(stem)

    words = [
        word
        for word in stem.split()
        if re.match(r"^[A-Za-z][A-Za-z.'-]*$", word)
    ]
    for size in (3, 2):
        if len(words) >= size:
            candidate = " ".join(words[:size])
            if looks_like_person_name(candidate):
                return title_case_name(candidate)

    return ""


def clean_line(line):
    return re.sub(r"\s+", " ", line).strip(" |:-•*")


def strip_name_prefix(line):
    return re.sub(r"^(name|candidate name|full name)\s*[:|-]\s*", "", line, flags=re.IGNORECASE).strip()


def should_skip_name_line(line):
    lowered = line.lower()
    
    # Combined target structural/phrase blocks to drop false entities early
    skip_terms = {
        "resume", "curriculum vitae", "cv", "email", "phone", "mobile", "contact",
        "linkedin", "github", "portfolio", "summary", "skills", "education", "experience",
        "projects", "certifications", "achievements", "languages", "school", "college",
        "university", "institute", "academy", "department", "bachelor", "master", "degree",
        "cgpa", "gpa", "percentage", "address", "permanent", "co-curricular", "hydrodynamic", "modelling",
        "spatial", "analytics", "location", "india", "technical", "skill", "skills", "traits",
        "personal traits", "contact me", "get in contact", "contact mobile", "profile",
        "project intern", "internship", "career objective", "professional summary", "objective",
        "personal details",
    }

    if any(term in lowered for term in skip_terms):
        return True
    if any(lowered.startswith(term + ":") for term in skip_terms):
        return True
    if re.match(r"^\[?page\s+\d+\]?$", line, flags=re.IGNORECASE):
        return True
    if line.count("|") >= 2:
        return True
    if "@" in line or re.search(r"https?://|www\.", line, flags=re.IGNORECASE):
        return True
    return False


def looks_like_person_name(value):
    value = value.strip()
    words = value.split()

    # Names are highly unlikely to be 1 word or over 4 words long in top context headers
    if len(words) < 2 or len(words) > 4:
        return False

    if len(value) > 40:
        return False

    # Check structural alphabetic integrity - supports initials (A.), hyphens, and apostrophes
    for word in words:
        if not re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word):
            return False

    # Prevent leakage of common corporate or non-human entity terms
    banned = ["limited", "private", "pvt", "company", "solutions", "services", "inc", "corp", "university", "college", "technologies", "technology", "systems", "software", "consulting", "consultancy", "analytics", "modelling", "engineering", "laboratories", "labs", "research"]
    lower = value.lower()
    if any(item in lower for item in banned):
        return False
    
    bad_phrases = [
        "curriculum vitae",
        "permanent address",
        "co-curricular",
        "hydrodynamic",
        "modelling",
        "spatial analytics",
        "objective",
        "summary",
        "career objective",
        "professional summary",
        "technical skills",
        "work experience",
        "personal details",
    ]

    if any(x in lower for x in bad_phrases):
        return False
    
    bad_exact = {
        "project intern",
        "personal traits",
        "technical skils",
        "technical skills",
        "get in contact",
        "contact mobile",
        "curriculum vitae",
        "cont act",
    }

    if value.lower() in bad_exact:
        return False

    return True


def title_case_name(value):
    # Helper fixed to match exact original intent with corrected syntax closing
    if value.isupper() or value.islower():
        return value.title()
    return value
