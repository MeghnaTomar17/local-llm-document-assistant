from __future__ import annotations

import logging
import os
import time
import requests
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

_http_session = requests.Session()
_http_session.mount("http://", HTTPAdapter(pool_connections=4, pool_maxsize=12))
_http_session.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=12))


class RequirementExtractionError(RuntimeError):
    """Raised when requirement extraction fails."""


class RequirementExtractor:
    """Uses Llama 3.2 to convert unstructured recruiter requirements to structured JSON."""

    def __init__(self, model: str | None = None, ollama_url: str | None = None) -> None:
        self.model = model or os.getenv("OLLAMA_CHAT_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3.2:3b"
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL") or "http://localhost:11434/api/generate"
        self.timeout_seconds = float(os.getenv("OLLAMA_CHAT_TIMEOUT_SECONDS", "300.0"))

    def extract(self, requirement_text: str) -> str:
        """Call Llama 3.2 and return raw JSON string."""
        clean_req = str(requirement_text or "").strip()
        if not clean_req:
            raise RequirementExtractionError("Requirement text is empty.")

        prompt = self.build_prompt(clean_req)
        
        try:
            started = time.perf_counter()
            response = _http_session.post(
                self.ollama_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0,
                    },
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            latency = time.perf_counter() - started
            
            raw_json = response.json().get("response", "").strip()
            logger.info("Extracted requirement JSON from model=%s in %.3fs", self.model, latency)
            return raw_json
            
        except requests.Timeout as exc:
            raise RequirementExtractionError("Ollama extraction timed out.") from exc
        except requests.ConnectionError as exc:
            raise RequirementExtractionError("Could not connect to Ollama.") from exc
        except requests.RequestException as exc:
            raise RequirementExtractionError("Ollama extraction API request failed.") from exc

    def build_prompt(self, requirement_text: str) -> str:
        """Construct the prompt instructing Llama 3.2 to act as a structured NLU parser."""
        return f"""You are an Enterprise Recruitment Requirement Extraction Agent.
Your only task is to analyze recruiter search queries or job descriptions and convert them into a structured JSON object.

You must output ONLY valid JSON matching the schema below.
Never write conversational text, markdown wrapping (no ```json code blocks), or explanations.

Expected JSON schema:
{{
  "role": "extracted job title, designation, or role name, or null if not specified",
  "experience": {{
    "minimum": integer number of minimum experience years requested, or null if not specified
  }},
  "mandatory_skills": ["array of skills explicitly marked as mandatory or required"],
  "preferred_skills": ["array of preferred or nice-to-have skills"],
  "gis_skills": ["array of GIS specific software, libraries, tools, or SDKs"],
  "programming_languages": ["array of programming languages"],
  "frameworks": ["array of software frameworks"],
  "databases": ["array of database systems"],
  "cloud": ["array of cloud platforms or cloud service tools"],
  "tools": ["array of development tools, software, or utilities"],
  "education": ["array of degrees, majors, or schooling requirements"],
  "certifications": ["array of professional certifications"],
  "location": ["array of city or geographical locations requested"],
  "candidate_type": "INTERNAL" or "EXTERNAL" if candidate pool is explicitly requested, else null,
  "fresher": boolean value (true if freshers, entry-level, or graduates are requested; false if experienced candidates are requested; else null),
  "interview_requirement": boolean value (true if candidates marked/cleared for interview are requested, else null)
}}

Instructions:
1. Do not invent any values. If a field cannot be found or inferred from the text, use null or [].
2. Set "candidate_type" to "INTERNAL" ONLY if the query explicitly contains words like "internal", "employee", "staff", or "in-house". Set it to "EXTERNAL" ONLY if the query explicitly contains words like "external", "vendor", "contractor", or "agency". If neither is explicitly mentioned, you MUST set "candidate_type" to null.
3. If they ask for "freshers", "graduates", "entry level", set "fresher" to true. If they ask for "experienced", "senior", or "lead", set "fresher" to false.
4. If they request candidates who have been marked/invited/cleared for an interview or "interview requirement", set "interview_requirement" to true.
5. Ignore company descriptions, culture, benefits, compensation, EEO statements, and marketing paragraphs.
6. Never generate SQL. Never expand synonyms. Extract only hiring requirements.

Recruiter input text to analyze:
<requirement>
{requirement_text}
</requirement>

JSON output:
"""
