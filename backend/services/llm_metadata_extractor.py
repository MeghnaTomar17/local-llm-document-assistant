"""LLM-first resume metadata extraction with strict output validation."""

import json
import logging
import os
import re

import requests


logger = logging.getLogger(__name__)
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = os.getenv("OLLAMA_METADATA_MODEL", "llama3.2:3b")
DEFAULT_MAX_LINES = int(os.getenv("OLLAMA_METADATA_MAX_LINES", "80"))
MIN_CONTEXT_LINES = 30
MAX_CONTEXT_LINES = 120
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_METADATA_TIMEOUT_SECONDS", "300"))

MODEL_ALIASES = {
    "llama3.2": "llama3.2:3b",
    "llama3.2:3b": "llama3.2:3b",
    "llama": "llama3.2:3b",
    "qwen2.5:3b": "qwen2.5:3b",
    "mistral": "mistral:latest",
    "gemma": "gemma2:2b",
}

EMPTY_METADATA = {
    "candidate_name": "",
    "email": "",
    "phone_number": "",
    "alternate_phone_numbers": [],
}
EMPTY_ENRICHMENT = {
    "skills": [],
    "cities": [],
}


class LLMMetadataExtractor:
    def __init__(self, model=None, ollama_url=None, max_lines=DEFAULT_MAX_LINES, timeout=None):
        self.model = resolve_model_name(model or DEFAULT_MODEL)
        self.ollama_url = ollama_url or DEFAULT_OLLAMA_URL
        self.max_lines = max(MIN_CONTEXT_LINES, min(MAX_CONTEXT_LINES, int(max_lines)))
        self.timeout = timeout or DEFAULT_TIMEOUT_SECONDS

    def extract(self, text):
        context = first_resume_lines(text, self.max_lines)
        if not context:
            return dict(EMPTY_METADATA)

        try:
            ollama_response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": build_metadata_prompt(context),
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0,
                        "num_predict": 120,
                    }
                },
                timeout=self.timeout,
            )
            ollama_response.raise_for_status()
            raw_response = ollama_response.json().get("response", "")
            logger.info("Ollama metadata raw output: %s", raw_response)
        except Exception as exc:
            logger.warning("Ollama metadata extraction failed: %s", exc)
            return dict(EMPTY_METADATA)

        return parse_and_validate_metadata(raw_response)


def extract_metadata_with_ollama(text, model=None, max_lines=DEFAULT_MAX_LINES):
    return LLMMetadataExtractor(model=model, max_lines=max_lines).extract(text)

def extract_enrichment_with_ollama(
    text,
    model=None,
    max_lines=DEFAULT_MAX_LINES,
):
    context = first_resume_lines(text, max_lines)

    if not context:
        return dict(EMPTY_ENRICHMENT)

    try:
        response = requests.post(
            DEFAULT_OLLAMA_URL,
            json={
                "model": resolve_model_name(
                    model or DEFAULT_MODEL
                ),
                "prompt": build_enrichment_prompt(context),
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_predict": 250,
                },
            },
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        raw_response = response.json().get(
            "response",
            "",
        )

    except Exception as exc:
        logger.warning(
            "Ollama enrichment extraction failed: %s",
            exc,
        )
        return dict(EMPTY_ENRICHMENT)

    return parse_and_validate_enrichment(
        raw_response
    )


def resolve_model_name(model):
    clean = str(model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(clean.lower(), clean)

def first_resume_lines(text, max_lines=DEFAULT_MAX_LINES):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]

    cleaned = []

    for line in lines:
        line = re.sub(
            r'\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b',
            lambda m: m.group(0).replace(" ", ""),
            line
        )
        cleaned.append(line)

    return "\n".join(cleaned[:max_lines])


def build_metadata_prompt(context):
    return f"""
Extract only this resume metadata. Return ONLY JSON:
{{
    "candidate_name": "...",
    "email": "...",
    "phone_number": "...",
    "alternate_phone_numbers": []
}}

Rules:
- Use only information explicitly present in the resume text.
- candidate_name must be the person's full name, not a company, role, heading, location, or school.
- Do not invent missing values. Use an empty string when unavailable.
- If one phone number exists, return it in phone_number.
- If multiple candidate phone numbers exist, return the first one in phone_number.
- Put all additional candidate phone numbers in alternate_phone_numbers.
- Ignore phone numbers belonging to references, emergency contacts, certifications, IDs, institutions, or other people.
- Candidate name is usually near the email address and phone number at the top of the resume.
- Do not return email usernames.
- Do not return addresses, districts, states, locations, institutions, headings, objectives, or section titles.
- Never construct candidate names from email usernames.
- Prefer the actual written name appearing in the resume.


Resume text:
{context}
""".strip()

def build_enrichment_prompt(context):
    return f"""
Extract ONLY the following information.

Return ONLY JSON:

{{
    "skills": [],
    "cities": [],

}}

Rules:

- Extract technical skills only.
- Ignore soft skills.
- Include programming languages, databases,
  GIS tools, cloud tools, frameworks,
  libraries and software tools.

- Extract only city names.

- Do not return states.
- Do not return countries.
- Do not return districts.
- Do not return taluks.
- Do not return blocks.
- Do not return villages.
- Do not return pincodes.
- Do not return full addresses.

- Return only actual city names.

Examples:

Good:
["Chennai", "Bengaluru", "Trivandrum"]

Bad:
["Tamil Nadu", "India", "Kanyakumari District", "Athoor Block"]



Resume text:
{context}
""".strip()



def parse_and_validate_metadata(raw_response):
    data = parse_json_object(raw_response)
    if not data:
        return dict(EMPTY_METADATA)
    return {
        "candidate_name": validate_candidate_name(data.get("candidate_name", "")),
        "email": validate_email(data.get("email", "")),
        "phone_number": validate_phone(data.get("phone_number", "")),
        "alternate_phone_numbers": validate_phone_list(data.get("alternate_phone_numbers", [])),
    }

def parse_and_validate_enrichment(raw_response):
    data = parse_json_object(raw_response)

    if not data:
        return dict(EMPTY_ENRICHMENT)

    return {
        "skills": validate_skills(
            data.get("skills", [])
        ),

        "cities": validate_cities(
            data.get("cities", [])
        ),

    }



def parse_json_object(raw_response):
    if isinstance(raw_response, dict):
        return raw_response

    raw = str(raw_response or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def validate_candidate_name(value):
    name = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;|-")
    words = name.split()
    if len(words) == 1 and len(name) > 15:
        return ""
    if not 1 <= len(words) <= 6 or len(name) > 80:
        return ""
    if any(char.isdigit() for char in name):
        return ""
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
        return ""

    lowered = name.lower()
    bad_names = {
        "resume",
        "curriculum vitae",
        "cv",
        "profile",
        "summary",
        "objective",
        "career objective",
        "academic profile",
        "academic details",
        "education",
        "experience",
        "work experience",
        "skills",
        "technical skills",
        "certifications",
        "certification",
        "projects",
        "languages",
        "contact",
        "personal details",
        "professional summary",
    }
    if lowered in bad_names:
        return ""
    
    if re.search(r"(gmail|yahoo|hotmail|outlook|cse|ece|it|mech|civil)$", lowered):
        return ""
    
    return name.title() if name.isupper() or name.islower() else name


def validate_email(value):
    email = str(value or "").strip().strip("<>,;")
    if re.fullmatch(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", email):
        return email
    return ""

def validate_city(value):
    city = re.sub(r"\s+", " ", str(value or "")).strip(" .,:;|-")

    if not city:
        return ""

    if len(city) < 2 or len(city) > 40:
        return ""

    if any(char.isdigit() for char in city):
        return ""

    if not re.fullmatch(r"[A-Za-z .'-]+", city):
        return ""

    lower = city.lower()

    bad_terms = {
        "india",
        "tamil nadu",
        "kerala",
        "karnataka",
        "andhra pradesh",
        "telangana",
        "west bengal",
        "maharashtra",
        "gujarat",
        "district",
        "taluk",
        "block",
        "street",
        "road",
        "village",
        "technology",
        "technologies",
        "software",
        "solutions",
        "private",
        "limited",
        "ltd",
        "pvt",
        "company",
        "office",
    }

    if lower in bad_terms:
        return ""

    if any(term in lower for term in [
        "district",
        "taluk",
        "block",
        "street",
        "road",
        "village",
        "technology",
        "software",
        "solutions",
        "company",
    ]):
        return ""

    if len(city.split()) > 3:
        return ""

    return city.title()

def validate_cities(values):
    if not isinstance(values, list):
        return []

    cleaned = []

    for city in values:
        valid_city = validate_city(city)

        if valid_city:
            cleaned.append(valid_city)

    return list(dict.fromkeys(cleaned))


def validate_phone_list(values):

    if not isinstance(values, list):
        return []

    validated = []

    for value in values:

        phone = validate_phone(value)

        if phone:
            validated.append(phone)

    return list(dict.fromkeys(validated))


def validate_phone(value):
    phone = str(value or "").strip()

    # Reject dates / year ranges
    if re.search(r"\b\d{1,2}/\d{4}\b", phone):
        return ""

    if "present" in phone.lower():
        return ""

    if re.search(r"\b(19|20)\d{2}\b", phone):
        return ""

    phone = re.sub(r"\s+", " ", phone).strip(" .,-")

    if not re.fullmatch(r"\+?[\d\s().-]+", phone):
        return ""

    digits = re.sub(r"\D", "", phone)

    return phone if 10 <= len(digits) <= 15 else ""

def validate_skills(skills):

    if not isinstance(skills, list):
        return []

    bad_patterns = [
        r"cgpa",
        r"gpa",
        r"percentage",
        r"mark",
        r"score",
        r"english",
        r"tamil",
        r"hindi",
        r"bengali",
        r"mother tongue",
        r"date of birth",
        r"nationality",
        r"address",
        r"phone",
        r"email",
        r"hard working",
        r"fast learner",
        r"team player",
        r"leadership",
        r"communication skills?",
        r"problem solving",
        r"self motivated",
    ]

    validated = []

    for skill in skills:

        skill = str(skill).strip()

        if len(skill) < 2:
            continue

        if len(skill) > 80:
            continue

        if any(
            re.search(pattern, skill, re.IGNORECASE)
            for pattern in bad_patterns
        ):
            continue

        validated.append(skill)

    return list(dict.fromkeys(validated))

def validate_experience(value):

    value = str(value).strip()

    if value == "-":
        return "-"

    try:

        years = float(value)

        if years < 0:
            return "0"

        if years > 50:
            return "-"

        return str(round(years, 1))

    except:
        return "-"
    
def _legacy_is_fresher_keyword_match(text):

    text_lower = str(text).lower()

    experience_sections = [
        "professional experience",
        "work experience",
        "employment history",
        "career history",
        "work history",
        "professional background",
    ]

    internship_sections = [
        "internship",
        "intern",
        "summer internship",
        "industrial training",
        "training program",
    ]

    # Any experience section found
    if any(section in text_lower for section in experience_sections):
        return False

    # Internship/training found
    if any(section in text_lower for section in internship_sections):
        return False

    # Professional designations with dates
    designation_patterns = [
        r'\bgis analyst\b',
        r'\bdeveloper\b',
        r'\bsoftware engineer\b',
        r'\bengineer\b',
        r'\bmanager\b',
        r'\bconsultant\b',
        r'\bexecutive\b',
        r'\banalyst\b',
        r'\bassociate\b',
        r'\bspecialist\b',
    ]

    has_designation = any(
        re.search(pattern, text_lower)
        for pattern in designation_patterns
    )

    has_dates = bool(
        re.search(
            r'20\d{2}\s*[-–]\s*(present|current|20\d{2})',
            text_lower,
            flags=re.IGNORECASE,
        )
    )

    if has_designation and has_dates:
        return False

    return True


EXPERIENCE_SECTION_HEADERS = (
    "experience",
    "experiences",
    "professional experience",
    "professional experiences",
    "professional work experience",
    "work experience",
    "work experiences",
    "working experience",
    "employment experience",
    "employment",
    "employment details",
    "employment history",
    "career history",
    "career experience",
    "work history",
    "professional background",
    "relevant experience",
    "industry experience",
    "positions held",
)

NON_EXPERIENCE_SECTION_HEADERS = (
    "education",
    "academic background",
    "qualification",
    "qualifications",
    "technical skills",
    "skills",
    "projects",
    "academic projects",
    "personal projects",
    "certifications",
    "certification",
    "courses",
    "workshops",
    "achievements",
    "awards",
    "activities",
    "languages",
    "interests",
    "hobbies",
    "summary",
    "profile",
    "objective",
    "declaration",
    "references",
)

NON_PROFESSIONAL_PATTERNS = (
    r"\bintern(ship)?s?\b",
    r"\bsummer intern(ship)?\b",
    r"\bwinter intern(ship)?\b",
    r"\bindustrial training\b",
    r"\btraining program(me)?\b",
    r"\btrainee\b",
    r"\bapprentice(ship)?\b",
    r"\bacademic project\b",
    r"\bcollege project\b",
    r"\bminor project\b",
    r"\bmajor project\b",
    r"\bcapstone\b",
    r"\bcertification\b",
    r"\bworkshop\b",
)

EMPLOYMENT_TYPE_PATTERNS = (
    r"\bfull[-\s]?time\b",
    r"\bpart[-\s]?time\b",
    r"\bcontract(or)?\b",
    r"\bfreelanc(e|er|ing)\b",
    r"\bconsult(ant|ing)\b",
    r"\bpermanent\b",
    r"\bemployee\b",
    r"\bpayroll\b",
)

PROFESSIONAL_ROLE_PATTERNS = (
    r"\bsoftware engineer\b",
    r"\bengineer\b",
    r"\bdeveloper\b",
    r"\bprogrammer\b",
    r"\banalyst\b",
    r"\bconsultant\b",
    r"\bmanager\b",
    r"\bexecutive\b",
    r"\bassociate\b",
    r"\bspecialist\b",
    r"\badministrator\b",
    r"\barchitect\b",
    r"\bdesigner\b",
    r"\btester\b",
    r"\bqa\b",
    r"\bcoordinator\b",
    r"\bofficer\b",
    r"\blead\b",
    r"\bsupervisor\b",
    r"\bgraphic designer\b",
    r"\bdigital designer\b",
    r"\bsupport engineer\b",
    r"\btechnical support\b",
    r"\bapplication support\b",
)

DATE_RANGE_PATTERN = re.compile(
    r"\(?\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)?\s*"
    r"(?:19|20)\d{2}\s*(?:-|to|till|until)\s*"
    r"(?:present|current|now|till\s+date|date|(?:19|20)\d{2}|"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)?\s*(?:19|20)\d{2})\b\)?",
    re.IGNORECASE,
)

DURATION_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\+?\s*(?:years?|yrs?|months?|mos?)\b",
    re.IGNORECASE,
)

COMPANY_SIGNAL_PATTERN = re.compile(
    r"\b(?:pvt\.?|ltd\.?|private limited|inc\.?|llc|llp|corp\.?|"
    r"corporation|company|technologies|technology|solutions|systems|"
    r"services|consultancy|labs|global)\b",
    re.IGNORECASE,
)


def _normalize_resume_text(text):
    normalized = str(text or "")
    normalized = normalized.replace("\u00a0", " ")
    normalized = normalized.replace("\u2013", "-").replace("\u2014", "-")
    normalized = normalized.replace("\u00e2\u20ac\u201c", "-")
    normalized = normalized.replace("\u00e2\u20ac\u009d", "-")
    return normalized


def _clean_header_line(line):
    line = re.sub(r"^[\s\-\u2022*#|:]+", "", line.strip().lower())
    line = re.sub(r"^\[page\s+\d+\]\s*", "", line)
    line = re.sub(r"[\s:|/_\-]+$", "", line)
    line = re.sub(r"\s+", " ", line)
    return line


def _is_section_header(line, headers):
    cleaned = _clean_header_line(line)

    if not cleaned or len(cleaned.split()) > 5:
        return False

    if cleaned in headers:
        return True

    return any(
        header in cleaned
        and re.fullmatch(rf"(?:[\w& ]+\s+)?{re.escape(header)}(?:\s+[\w& ]+)?", cleaned)
        for header in headers
    )


def _extract_experience_sections(text):
    lines = _normalize_resume_text(text).splitlines()
    sections = []
    current = []
    in_experience = False

    all_known_headers = set(EXPERIENCE_SECTION_HEADERS) | set(NON_EXPERIENCE_SECTION_HEADERS)

    for line in lines:
        if _is_section_header(line, EXPERIENCE_SECTION_HEADERS):
            if current:
                sections.append("\n".join(current))
            current = []
            in_experience = True
            continue

        if in_experience and _is_section_header(line, all_known_headers):
            if current:
                sections.append("\n".join(current))
            current = []
            in_experience = False
            continue

        if in_experience:
            current.append(line)

    if current:
        sections.append("\n".join(current))

    return [section for section in sections if section.strip()]


def _split_experience_entries(section_text):
    lines = [line.strip() for line in section_text.splitlines()]
    entries = []
    current = []

    for line in lines:
        if not line:
            if current:
                entries.append(" ".join(current))
                current = []
            continue

        starts_new_entry = bool(
            current
            and (
                DATE_RANGE_PATTERN.search(line)
                or re.match(r"^[\-\u2022*]\s+", line)
            )
        )

        if starts_new_entry:
            entries.append(" ".join(current))
            current = []

        current.append(line)

        if len(current) >= 5:
            entries.append(" ".join(current))
            current = []

    if current:
        entries.append(" ".join(current))

    non_empty_lines = [line for line in lines if line]
    for index in range(len(non_empty_lines)):
        entries.append(" ".join(non_empty_lines[index:index + 4]))
        entries.append(" ".join(non_empty_lines[index:index + 6]))

    return entries


def _has_any_pattern(text, patterns):
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _is_non_professional_entry(entry):
    return _has_any_pattern(entry, NON_PROFESSIONAL_PATTERNS)


def _entry_before_first_non_professional_signal(entry):
    matches = [
        match.start()
        for pattern in NON_PROFESSIONAL_PATTERNS
        for match in re.finditer(pattern, entry, flags=re.IGNORECASE)
    ]

    if not matches:
        return entry

    return entry[:min(matches)].strip()


def _is_professional_entry(entry):
    if not entry:
        return False

    if _is_non_professional_entry(entry):
        professional_prefix = _entry_before_first_non_professional_signal(entry)
        if not professional_prefix:
            return False
        entry = professional_prefix

    has_role = _has_any_pattern(entry, PROFESSIONAL_ROLE_PATTERNS)
    has_employment_type = _has_any_pattern(entry, EMPLOYMENT_TYPE_PATTERNS)
    has_dates = bool(DATE_RANGE_PATTERN.search(entry) or DURATION_PATTERN.search(entry))
    has_company_signal = bool(COMPANY_SIGNAL_PATTERN.search(entry))
    has_work_signal = bool(
        re.search(
            r"\b(?:roles?\s+and\s+responsibilit(?:y|ies)|worked\s+on|"
            r"working\s+on|service\s+request|incident\s+management|client\s*:)\b",
            entry,
            flags=re.IGNORECASE,
        )
    )

    if has_employment_type and (has_role or has_dates or has_company_signal):
        return True

    if has_role and has_dates:
        return True

    if has_role and has_company_signal:
        return True

    if has_dates and has_work_signal:
        return True

    return False


def _has_explicit_zero_experience(text):
    return bool(
        re.search(
            r"\b(?:fresher|no\s+(?:work\s+|professional\s+)?experience|"
            r"0\s*(?:years?|yrs?)\s+(?:of\s+)?experience)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def is_fresher(text):
    """Return True when the resume has no deterministic professional job signal."""

    normalized_text = _normalize_resume_text(text)

    experience_sections = _extract_experience_sections(normalized_text)

    if experience_sections:
        return not any(
            _is_professional_entry(entry)
            for section in experience_sections
            for entry in _split_experience_entries(section)
        )

    compact_entries = _split_experience_entries(normalized_text)
    return not any(
        _is_professional_entry(entry)
        and (
            _has_any_pattern(entry, EMPLOYMENT_TYPE_PATTERNS)
            or COMPANY_SIGNAL_PATTERN.search(entry)
        )
        for entry in compact_entries
    )
