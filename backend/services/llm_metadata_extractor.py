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