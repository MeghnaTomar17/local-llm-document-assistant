from pathlib import Path
import csv
import re


METADATA_FIELDS = [
    "Resume File Name",
    "Candidate Name",
    "Email",
    "Phone Number",
]


class ResumeMetadataService:
    def __init__(self, output_dir="."):
        self.output_dir = Path(output_dir)
        self.records = []
        self.txt_path = self.output_dir / "metadata.txt"
        self.csv_path = self.output_dir / "metadata.csv"
        self.reset()

    def reset(self):
        self.records = []
        self.regenerate_files()

    def add_resume(self, file_name, extracted_text):
        record = extract_resume_metadata(file_name, extracted_text)
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


def extract_resume_metadata(file_name, extracted_text):
    text = extracted_text or ""
    return {
        "Resume File Name": file_name or "",
        "Candidate Name": extract_candidate_name(text) or extract_candidate_name_from_file_name(file_name),
        "Email": extract_email(text),
        "Phone Number": extract_phone_number(text),
    }


def extract_email(text):
    match = re.search(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", text)
    return match.group(0) if match else ""


def extract_phone_number(text):
    phone_patterns = [
        r"\+?\d[\d\s().-]{8,}\d",
        r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{4}",
    ]

    for pattern in phone_patterns:
        for match in re.finditer(pattern, text):
            candidate = normalize_phone(match.group(0))
            if is_plausible_phone(candidate):
                return candidate
    return ""


def normalize_phone(value):
    return re.sub(r"\s+", " ", value).strip(" .-")


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
    lines = [
        clean_line(line)
        for line in text.splitlines()[:30]
        if clean_line(line)
    ]

    candidates = []

    for line in lines:
        if should_skip_name_line(line):
            continue

        candidate = strip_name_prefix(line)

        if looks_like_person_name(candidate):
            candidates.append(candidate)

    if not candidates:
        return ""

    # Prefer ALL CAPS names (common in resumes)
    for candidate in candidates:
        if candidate.isupper():
            return candidate.title()

    # Prefer names with exactly 2 or 3 words
    for candidate in candidates:
        words = candidate.split()
        if 2 <= len(words) <= 3:
            return candidate

    return candidates[0]


def extract_candidate_name_from_file_name(file_name):
    if not file_name:
        return ""

    stem = Path(file_name).stem
    stem = re.sub(r"[_\-]+", " ", stem)
    stem = re.sub(r"\b(?:resume|cv|curriculum|vitae|final|latest|updated|copy|new|ats)\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\b(?:pdf|docx|doc)\b", " ", stem, flags=re.IGNORECASE)
    stem = re.sub(r"\d+", " ", stem)
    stem = clean_line(stem)

    if looks_like_person_name(stem):
        return title_case_name(stem)

    words = [
        word
        for word in stem.split()
        if re.match(r"^[A-Za-z][A-Za-z.'-]*$", word)
    ]
    for size in (3, 2):
        candidate = " ".join(words[:size])
        if looks_like_person_name(candidate):
            return title_case_name(candidate)

    return ""


def clean_line(line):
    return re.sub(r"\s+", " ", line).strip(" |:-")


def strip_name_prefix(line):
    return re.sub(r"^(name|candidate name|full name)\s*[:|-]\s*", "", line, flags=re.IGNORECASE).strip()


def should_skip_name_line(line):
    lowered = line.lower()
    skip_terms = {
        "resume",
        "curriculum vitae",
        "cv",
        "email",
        "phone",
        "mobile",
        "contact",
        "linkedin",
        "github",
        "portfolio",
        "summary",
        "skills",
        "education",
        "experience",
        "projects",
        "certifications",
        "achievements",
        "languages",
        "school",
        "college",
        "university",
        "institute",
        "academy",
        "department",
        "bachelor",
        "master",
        "degree",
        "cgpa",
        "gpa",
        "percentage",
        "intern",
        "developer",
        "engineer",
        "manager",
        "analyst",
        "consultant",
    }

    if any(term in lowered for term in skip_terms):
        return True
    if re.match(r"^\[?page\s+\d+\]?$", line, flags=re.IGNORECASE):
        return True
    if line.count("|") >= 2:
        return True
    if "@" in line or re.search(r"https?://|www\.", line, flags=re.IGNORECASE):
        return True
    if re.search(r"\d{3,}", line):
        return True
    return False


def looks_like_person_name(value):
    words = value.split()

    if not 2 <= len(words) <= 4:
        return False

    if len(value) > 50:
        return False

    banned = {
        "academic",
        "academy",
        "qualifications",
        "skills",
        "projects",
        "experience",
        "education",
        "school",
        "college",
        "university",
        "institute",
        "department",
        "bachelor",
        "master",
        "degree",
        "languages",
        "language",
        "about",
        "about me",
        "summary",
        "profile",
        "career",
        "objective",
        "contact",
        "technical",
        "professional",
        "certifications",
        "achievements",
        "building",
        "scalable",
        "platforms",
    }

    lower = value.lower()

    for word in banned:
        if word in lower:
            return False

    return all(
        re.match(r"^[A-Za-z][A-Za-z.'-]*$", word)
        for word in words
    )


def title_case_name(value):
    if value.isupper() or value.islower():
        return value.title()
    return value
