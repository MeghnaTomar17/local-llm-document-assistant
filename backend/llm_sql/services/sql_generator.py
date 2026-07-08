from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
from threading import RLock
import time

import requests
from requests.adapters import HTTPAdapter

from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator

_prompt_cache: dict[Path, str] = {}
_prompt_cache_lock = RLock()
_http_session = requests.Session()
_http_session.mount("http://", HTTPAdapter(pool_connections=4, pool_maxsize=12))
_http_session.mount("https://", HTTPAdapter(pool_connections=4, pool_maxsize=12))


logger = logging.getLogger(__name__)


class SQLGenerationError(RuntimeError):
    """Raised when SQL generation cannot be completed."""


@dataclass(frozen=True)
class SQLGeneratorConfig:
    """Configuration for SQL generation through Ollama."""

    model: str
    ollama_url: str = "http://localhost:11434/api/generate"
    timeout_seconds: float = 600.0
    schema_context_path: Path = Path(__file__).resolve().parents[1] / "prompts" / "schema_context.txt"
    prompt_template_path: Path = Path(__file__).resolve().parents[1] / "prompts" / "sql_prompt.txt"

    @classmethod
    def from_env(cls) -> "SQLGeneratorConfig":
        """Build configuration from environment variables."""

        model = os.getenv("OLLAMA_SQL_MODEL", "qwen2.5-coder:7b")

        return cls(
            model=model,
            ollama_url=os.getenv("OLLAMA_URL", cls.ollama_url),
            timeout_seconds=float(os.getenv("OLLAMA_SQL_TIMEOUT_SECONDS", "600")),
            schema_context_path=Path(
                os.getenv("OLLAMA_SQL_SCHEMA_CONTEXT_PATH", str(cls.schema_context_path))
            ),
            prompt_template_path=Path(
                os.getenv("OLLAMA_SQL_PROMPT_TEMPLATE_PATH", str(cls.prompt_template_path))
            ),
        )


@dataclass(frozen=True)
class SQLGenerationResult:
    """Generated SQL plus validation metadata."""

    sql: str
    validation: SQLValidationResult
    model: str
    latency_seconds: float


class SQLGenerator:
    """Generate PostgreSQL SELECT statements from recruiter questions."""

    def __init__(
        self,
        config: SQLGeneratorConfig | None = None,
        validator: SQLValidator | None = None,
    ) -> None:
        self.config = config or SQLGeneratorConfig.from_env()
        self.validator = validator or SQLValidator()
        self.schema_context = self._read_prompt_file(self.config.schema_context_path)
        self.prompt_template = self._read_prompt_file(self.config.prompt_template_path)

    def generate_sql(self, question: str) -> str:
        """Generate and return SQL only."""

        return self.generate(question).sql

    def generate(self, question: str) -> SQLGenerationResult:
        """Generate SQL and include validation metadata."""

        clean_question = str(question or "").strip()
        if not clean_question:
            raise SQLGenerationError("Recruiter question is required.")

        prompt = self.build_prompt(clean_question)
        started_at = time.perf_counter()

        try:
            raw_sql = self._call_ollama(prompt)
        except requests.Timeout as exc:
            raise SQLGenerationError("Ollama SQL generation timed out.") from exc
        except requests.ConnectionError as exc:
            raise SQLGenerationError("Could not connect to Ollama.") from exc
        except requests.RequestException as exc:
            raise SQLGenerationError("Ollama SQL generation failed.") from exc

        latency = time.perf_counter() - started_at
        sql = self.clean_sql(raw_sql)
        validation = self.validator.validate(sql)

        logger.info(
            "Generated SQL with model=%s latency=%.3fs valid=%s",
            self.config.model,
            latency,
            validation.is_valid,
        )

        return SQLGenerationResult(
            sql=sql,
            validation=validation,
            model=self.config.model,
            latency_seconds=latency,
        )

    def build_prompt(self, question: str) -> str:
        """Build the final prompt from schema context, template, and question."""

        return self.prompt_template.format(
            schema_context=self.schema_context,
            question=question,
        )

    @staticmethod
    def clean_sql(raw_sql: str) -> str:
        """Remove markdown wrappers and normalize generated SQL whitespace."""

        sql = str(raw_sql or "").strip()
        fenced_match = re.search(
            r"```(?:sql)?\s*(.*?)```",
            sql,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if fenced_match:
            sql = fenced_match.group(1).strip()

        sql = re.sub(r"^\s*SQL\s*:\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\s+", " ", sql).strip()
        return sql

    @staticmethod
    def _read_prompt_file(path: Path) -> str:
        resolved_path = path.resolve()
        with _prompt_cache_lock:
            if resolved_path in _prompt_cache:
                return _prompt_cache[resolved_path]
            if not resolved_path.exists():
                raise SQLGenerationError(f"Prompt file not found: {resolved_path}")

            content = resolved_path.read_text(encoding="utf-8").strip()
            _prompt_cache[resolved_path] = content
            return content

    def _call_ollama(self, prompt: str) -> str:
        response = _http_session.post(
            self.config.ollama_url,
            json={
                "model": self.config.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0,
                },
            },
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()
        return str(response.json().get("response", ""))
