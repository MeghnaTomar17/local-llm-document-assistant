"""Benchmark LLM-first resume metadata extraction against a ground-truth CSV."""
import time
import argparse
import csv
from pathlib import Path
import re

from backend.services.metadata_service import extract_resume_metadata
from pdf_processor import ALLOWED_EXTENSIONS, extract_text


TRUTH_FIELD_ALIASES = {
    "file_name": {"resume file name", "file name", "filename", "file", "resume"},
    "candidate_name": {"candidate name", "candidate_name", "name", "full name"},
    "email": {"email", "email address"},
    "phone_number": {"phone number", "phone_number", "phone", "mobile", "mobile number"},
}


def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM resume metadata extraction.")
    parser.add_argument("resume_folder", type=Path, help="Folder containing PDF and DOCX resumes.")
    parser.add_argument(
        "--ground-truth",
        type=Path,
        default=None,
        help="Ground-truth CSV path. Defaults to <resume_folder>/ground_truth.csv.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model or alias: llama3.2, qwen, mistral, or gemma.",
    )
    args = parser.parse_args()
    print("=" * 80)
    print(f"MODEL: {args.model}")
    print("=" * 80)

    ground_truth_path = args.ground_truth or args.resume_folder / "ground_truth.csv"
    truth = load_ground_truth(ground_truth_path)
    resumes = sorted(
        path
        for path in args.resume_folder.iterdir()
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS
    )

    if not resumes:
        raise SystemExit(f"No supported resumes found in {args.resume_folder}")

    totals = {"candidate_name": 0, "email": 0, "phone_number": 0}
    correct = {"candidate_name": 0, "email": 0, "phone_number": 0}
    evaluated_files = 0
    total_time = 0
    for resume_path in resumes:
        expected = truth.get(normalize_file_name(resume_path.name))
        if not expected:
            print(f"SKIP {resume_path.name}: no ground-truth row")
            continue

        extraction = extract_text(resume_path)
        start = time.perf_counter()
        predicted = extract_resume_metadata(
            resume_path.name,
            extraction.get("text", ""),
            llm_model=args.model,
        )
        elapsed = time.perf_counter() - start
        total_time += elapsed
        print("\nFINAL RECORD:")
        print(predicted)
        print("=" * 80)
        evaluated_files += 1
        mismatches = []

        comparisons = {
            "candidate_name": (predicted["Candidate Name"], expected["candidate_name"], normalize_text),
            "email": (predicted["Email"], expected["email"], normalize_text),
            "phone_number": (predicted["Phone Number"], expected["phone_number"], normalize_phone),
        }
        

        for field, (actual, target, normalizer) in comparisons.items():
            if not target:
                continue
            totals[field] += 1
            if normalizer(actual) == normalizer(target):
                correct[field] += 1
            else:
                mismatches.append(f"{field}: expected={target!r}, actual={actual!r}")

        print(f"{'PASS' if not mismatches else 'FAIL'} {resume_path.name}")
        for mismatch in mismatches:
            print(f"  {mismatch}")

    print("\nAccuracy")
    for field in ("candidate_name", "email", "phone_number"):
        accuracy = (correct[field] / totals[field] * 100) if totals[field] else 0.0
        print(f"{field}: {correct[field]}/{totals[field]} ({accuracy:.2f}%)")
    print(f"evaluated resumes: {evaluated_files}")
    if evaluated_files:
        print(
            f"\nAverage inference time: "
            f"{total_time/evaluated_files:.2f}s"
        )

    overall_correct = sum(correct.values())
    overall_total = sum(totals.values())

    overall_accuracy = (
        overall_correct / overall_total * 100
        if overall_total
        else 0
    )

    print(
        f"\nOVERALL: {overall_correct}/{overall_total} "
        f"({overall_accuracy:.2f}%)"
    )
    print("\n" + "=" * 80)
    print(f"MODEL: {args.model}")
    print(f"OVERALL: {overall_correct}/{overall_total} ({overall_accuracy:.2f}%)")
    print("=" * 80)


def load_ground_truth(path):
    if not path.exists():
        raise SystemExit(f"Ground-truth CSV was not found: {path}")

    records = {}
    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            normalized_row = {normalize_header(key): value.strip() for key, value in row.items() if key}
            file_name = find_alias_value(normalized_row, TRUTH_FIELD_ALIASES["file_name"])
            if not file_name:
                continue
            records[normalize_file_name(file_name)] = {
                "candidate_name": find_alias_value(normalized_row, TRUTH_FIELD_ALIASES["candidate_name"]),
                "email": find_alias_value(normalized_row, TRUTH_FIELD_ALIASES["email"]),
                "phone_number": find_alias_value(normalized_row, TRUTH_FIELD_ALIASES["phone_number"]),
            }
    return records


def find_alias_value(row, aliases):
    for alias in aliases:
        value = row.get(normalize_header(alias), "")
        if value:
            return value
    return ""


def normalize_header(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").strip().lower())


def normalize_file_name(value):
    return Path(str(value or "")).name.strip().lower()


def normalize_text(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def normalize_phone(value):
    value = re.sub(r"\b(?:19|20)\d{2}\b.*$", "", str(value or "")).strip()

    digits = re.sub(r"\D", "", value)

    # Indian number with country code
    if digits.startswith("91") and len(digits) == 12:
        return f"+91 {digits[2:]}"

    # Indian number with leading 0
    if digits.startswith("0") and len(digits) == 11:
        return digits

    # Standard 10 digit
    if len(digits) == 10:
        return digits

    # International numbers
    if 11 <= len(digits) <= 15:
        return value

    return ""

if __name__ == "__main__":
    main()
