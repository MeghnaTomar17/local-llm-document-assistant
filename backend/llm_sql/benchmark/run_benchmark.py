from __future__ import annotations

import csv
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
import sys
import time
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.llm_sql.services.recruiter_search_service import (  # noqa: E402
    RecruiterSearchService,
    SQLSearchValidationError,
)
from backend.llm_sql.services.sql_executor import (  # noqa: E402
    SQLExecutionError,
    SQLExecutionResult,
    SQLExecutor,
)
from backend.llm_sql.services.sql_generator import (  # noqa: E402
    SQLGenerationError,
    SQLGenerationResult,
    SQLGenerator,
    SQLGeneratorConfig,
)
from backend.llm_sql.services.sql_validator import SQLValidationResult, SQLValidator  # noqa: E402


logger = logging.getLogger(__name__)

BENCHMARK_MODELS = [
    "llama3.2:3b",
    "qwen2.5-coder:7b",
    "gemma3:4b",
    "deepseek-r1:8b",
]

BENCHMARK_DIR = Path(__file__).resolve().parent
QUERIES_PATH = BENCHMARK_DIR / "benchmark_queries.json"
RESULTS_PATH = BENCHMARK_DIR / "benchmark_results.csv"
SUMMARY_PATH = BENCHMARK_DIR / "model_summary.csv"

RESULT_FIELDS = [
    "model",
    "question",
    "generated_sql",
    "validation_pass",
    "execution_pass",
    "row_count",
    "sql_generation_time_ms",
    "sql_execution_time_ms",
    "total_time_ms",
    "error_message",
]

SUMMARY_FIELDS = [
    "model",
    "total_queries",
    "validation_pass_rate",
    "execution_success_rate",
    "average_generation_time_ms",
    "average_execution_time_ms",
    "average_total_time_ms",
]


@dataclass
class CapturingSQLGenerator:
    inner: SQLGenerator
    last_result: SQLGenerationResult | None = None

    def generate(self, question: str) -> SQLGenerationResult:
        self.last_result = self.inner.generate(question)
        return self.last_result


@dataclass
class CapturingSQLExecutor:
    inner: SQLExecutor
    last_result: SQLExecutionResult | None = None

    def execute(self, validation: SQLValidationResult) -> SQLExecutionResult:
        self.last_result = self.inner.execute(validation)
        return self.last_result


def load_queries(path: Path = QUERIES_PATH) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_search_service(model: str) -> tuple[RecruiterSearchService, CapturingSQLGenerator, CapturingSQLExecutor]:
    validator = SQLValidator()
    generator = CapturingSQLGenerator(
        SQLGenerator(
            config=SQLGeneratorConfig(
                model=model,
                ollama_url=os.getenv(
                    "OLLAMA_URL",
                    SQLGeneratorConfig.ollama_url,
                ),
            ),
            validator=validator,
        )
    )
    executor = CapturingSQLExecutor(SQLExecutor())
    service = RecruiterSearchService(
        generator=generator,
        validator=validator,
        executor=executor,
    )
    return service, generator, executor


def benchmark_query(model: str, question: str, service: RecruiterSearchService, generator: CapturingSQLGenerator, executor: CapturingSQLExecutor) -> dict[str, Any]:
    started_at = time.perf_counter()
    error_message = ""
    generated_sql = ""
    validation_pass = False
    execution_pass = False
    row_count = 0
    generation_time_ms = 0.0
    execution_time_ms = 0.0

    try:
        response = service.search(question)
        generated_sql = response.generated_sql
        validation_pass = True
        execution_pass = True
        row_count = response.row_count

    except SQLSearchValidationError as exc:
        generated_sql = exc.generated_sql
        error_message = str(exc)
        validation_pass = False
        execution_pass = False

    except (SQLGenerationError, SQLExecutionError) as exc:
        error_message = str(exc)
        validation_pass = bool(
            generator.last_result
            and generator.last_result.validation.is_valid
        )
        execution_pass = False

    except Exception as exc:
        logger.exception(
            "Unexpected benchmark failure model=%s question=%s",
            model,
            question,
        )
        error_message = str(exc)
        validation_pass = bool(
            generator.last_result
            and generator.last_result.validation.is_valid
        )
        execution_pass = False

    if generator.last_result:
        generated_sql = generated_sql or generator.last_result.sql
        validation_pass = validation_pass or generator.last_result.validation.is_valid
        generation_time_ms = generator.last_result.latency_seconds * 1000

    if executor.last_result:
        execution_time_ms = executor.last_result.execution_time_ms
        row_count = executor.last_result.row_count

    total_time_ms = (time.perf_counter() - started_at) * 1000

    logger.info(
        "Benchmark query completed model=%s validation_pass=%s execution_pass=%s "
        "generation_ms=%.2f execution_ms=%.2f total_ms=%.2f rows=%s error=%s",
        model,
        validation_pass,
        execution_pass,
        generation_time_ms,
        execution_time_ms,
        total_time_ms,
        row_count,
        error_message,
    )

    return {
        "model": model,
        "question": question,
        "generated_sql": generated_sql,
        "validation_pass": validation_pass,
        "execution_pass": execution_pass,
        "row_count": row_count,
        "sql_generation_time_ms": round(generation_time_ms, 3),
        "sql_execution_time_ms": round(execution_time_ms, 3),
        "total_time_ms": round(total_time_ms, 3),
        "error_message": error_message,
    }


def summarize_model(model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_queries = len(rows)
    validation_passes = sum(1 for row in rows if row["validation_pass"])
    execution_passes = sum(1 for row in rows if row["execution_pass"])

    return {
        "model": model,
        "total_queries": total_queries,
        "validation_pass_rate": _rate(validation_passes, total_queries),
        "execution_success_rate": _rate(execution_passes, total_queries),
        "average_generation_time_ms": _average(row["sql_generation_time_ms"] for row in rows),
        "average_execution_time_ms": _average(row["sql_execution_time_ms"] for row in rows),
        "average_total_time_ms": _average(row["total_time_ms"] for row in rows),
    }


def _rate(count: int, total: int) -> float:
    return round((count / total) * 100, 2) if total else 0.0


def _average(values) -> float:
    values = [float(value) for value in values]
    return round(sum(values) / len(values), 3) if values else 0.0


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_model_summary(summary: dict[str, Any]) -> None:
    print("=" * 48)
    print(f"Model : {summary['model']}")
    print(f"Queries : {summary['total_queries']}")
    print(f"Validation : {summary['validation_pass_rate']}%")
    print(f"Execution : {summary['execution_success_rate']}%")
    print(f"Avg Generation : {summary['average_generation_time_ms']} ms")
    print(f"Avg Execution : {summary['average_execution_time_ms']} ms")
    print(f"Avg Total : {summary['average_total_time_ms']} ms")
    print("=" * 48)


def run_benchmark(models: list[str] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queries = load_queries()
    benchmark_models = models or BENCHMARK_MODELS
    all_results: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []

    for model in benchmark_models:
        logger.info("Starting benchmark for model=%s query_count=%s", model, len(queries))
        model_rows: list[dict[str, Any]] = []

        try:
            service, generator, executor = build_search_service(model)
        except Exception as exc:
            logger.exception("Failed to initialize benchmark pipeline for model=%s", model)
            for query in queries:
                row = failed_query_row(
                    model=model,
                    question=query["question"],
                    error_message=f"Pipeline initialization failed: {exc}",
                )
                model_rows.append(row)
                all_results.append(row)

            summary = summarize_model(model, model_rows)
            summaries.append(summary)
            print_model_summary(summary)
            continue

        for query in queries:
            generator.last_result = None
            executor.last_result = None
            question = query["question"]
            logger.info("Benchmarking model=%s question=%s", model, question)
            row = benchmark_query(model, question, service, generator, executor)
            model_rows.append(row)
            all_results.append(row)

        summary = summarize_model(model, model_rows)
        summaries.append(summary)
        print_model_summary(summary)

    write_csv(RESULTS_PATH, RESULT_FIELDS, all_results)
    write_csv(SUMMARY_PATH, SUMMARY_FIELDS, summaries)
    logger.info("Benchmark results written to %s", RESULTS_PATH)
    logger.info("Benchmark summary written to %s", SUMMARY_PATH)

    return all_results, summaries


def failed_query_row(model: str, question: str, error_message: str) -> dict[str, Any]:
    return {
        "model": model,
        "question": question,
        "generated_sql": "",
        "validation_pass": False,
        "execution_pass": False,
        "row_count": 0,
        "sql_generation_time_ms": 0.0,
        "sql_execution_time_ms": 0.0,
        "total_time_ms": 0.0,
        "error_message": error_message,
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run_benchmark()
