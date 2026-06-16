"""LLM-first resume metadata extraction with strict output validation."""

import json
import os
import re
from urllib import response

import requests


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
DEFAULT_MODEL = "llama3.2:3b"
DEFAULT_MAX_LINES = 30
MIN_CONTEXT_LINES = 20
MAX_CONTEXT_LINES = 40
DEFAULT_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_METADATA_TIMEOUT_SECONDS", "60"))

MODEL_ALIASES = {
    "llama": "llama3.2:3b",
    "llama3.2": "llama3.2:3b",
}

EMPTY_METADATA = {
    "candidate_name": "",
    "email": "",
    "phone_number": "",
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
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": build_metadata_prompt(context),
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0
                    }
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            raw_response = response.json().get("response", "")
        except Exception as e:
            print("=" * 80)
            print("OLLAMA ERROR")
            print(e)
            print("=" * 80)
            raise

        return parse_and_validate_metadata(raw_response)


def extract_metadata_with_ollama(text, model=None, max_lines=DEFAULT_MAX_LINES):
    return LLMMetadataExtractor(model=model, max_lines=max_lines).extract(text)


def resolve_model_name(model):
    clean = str(model or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(clean.lower(), clean)


def first_resume_lines(text, max_lines=DEFAULT_MAX_LINES):
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def build_metadata_prompt(context):
    return f"""
Extract resume metadata from the supplied text.

Return ONLY a JSON object with the following keys: candidate_name, email, phone_number:
{{
  "candidate_name": "...",
  "email": "...",
  "phone_number": "..."
}}

Rules:
- Use only information explicitly present in the resume text.
- candidate_name must be the person's full name, not a company, role, heading, location, or institution.
- Do not invent missing values. Use an empty string when unavailable.
- Do not add markdown, explanation, or extra keys.

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
    if not 1 <= len(words) <= 6 or len(name) > 80:
        return ""
    if any(char.isdigit() for char in name):
        return ""
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
        return ""

    lowered = name.lower()
    if re.fullmatch(
        r"(resume|curriculum vitae|cv|profile|summary|objective|skills?|education|experience|"
        r"projects?|certifications?|achievements?|languages?|contact|personal details?)",
        lowered,
    ):
        return ""
    return name.title() if name.isupper() or name.islower() else name


def validate_email(value):
    email = str(value or "").strip().strip("<>,;")
    if re.fullmatch(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", email):
        return email
    return ""


def validate_phone(value):
    phone = re.sub(r"\s+", " ", str(value or "")).strip(" .,-")
    if not re.fullmatch(r"\+?[\d\s().-]+", phone):
        return ""
    digits = re.sub(r"\D", "", phone)
    return phone if 10 <= len(digits) <= 15 else ""
