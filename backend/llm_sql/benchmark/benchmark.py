from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from backend.llm_sql.services.sql_generator import SQLGenerator, SQLGeneratorConfig


logger = logging.getLogger(__name__)


DEFAULT_QUERIES_PATH = Path(__file__).with_name("benchmark_queries.json")


def load_benchmark_queries(path: Path = DEFAULT_QUERIES_PATH) -> list[dict[str, str]]:
    """Load recruiter questions for later model benchmarking."""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def configured_benchmark_models() -> list[str]:
    """Return model names from OLLAMA_SQL_BENCHMARK_MODELS."""

    raw_models = os.getenv("OLLAMA_SQL_BENCHMARK_MODELS", "")
    return [model.strip() for model in raw_models.split(",") if model.strip()]


def run_generation_benchmark(
    models: list[str] | None = None,
    queries_path: Path = DEFAULT_QUERIES_PATH,
) -> list[dict]:
    """Generate SQL for each query/model pair without executing SQL."""

    benchmark_models = models or configured_benchmark_models()
    if not benchmark_models:
        raise ValueError("Provide models or set OLLAMA_SQL_BENCHMARK_MODELS.")

    queries = load_benchmark_queries(queries_path)
    results: list[dict] = []

    for model in benchmark_models:
        generator = SQLGenerator(
            config=SQLGeneratorConfig(
                model=model,
                ollama_url=os.getenv(
                    "OLLAMA_URL",
                    SQLGeneratorConfig.ollama_url,
                ),
            )
        )

        for query in queries:
            result = generator.generate(query["question"])
            results.append(
                {
                    "model": model,
                    "query_id": query["id"],
                    "question": query["question"],
                    "sql": result.sql,
                    "is_valid": result.validation.is_valid,
                    "errors": result.validation.errors,
                    "latency_seconds": result.latency_seconds,
                }
            )

            logger.info(
                "Benchmarked model=%s query=%s valid=%s",
                model,
                query["id"],
                result.validation.is_valid,
            )

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(run_generation_benchmark(), indent=2))
