from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path

from tqdm import tqdm

from backend.services.bulk_status import finish_bulk_import, start_bulk_import, update_bulk_progress, utc_now, mark_bulk_import_interrupted
from backend.services.resume_service import DuplicateCandidateError
from backend.services.document_service import document_service
from backend.services.infrastructure import (
    InfrastructureError,
    database_health_check,
    retry_database_operation,
)


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

REPORT_FILE = "processing_report.csv"
LOG_FILE = "bulk_processing.log"
RETRY_MANIFEST_FILE = Path("bulk_retry_manifest.json")
MAX_CONSECUTIVE_INFRA_FAILURES = 5
DB_RECOVERY_CHECKS = 6
DB_RECOVERY_DELAY_SECONDS = 10

STATUS_INFRASTRUCTURE_FAILED = "INFRASTRUCTURE_FAILED"
STATUS_UNPROCESSED = "UNPROCESSED"


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------
# Argument Parsing
# ---------------------------------------------------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Bulk Resume Processing Utility"
    )

    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder containing resumes",
    )

    parser.add_argument(
        "--session",
        dest="session_id",
        help="Existing persistent session UUID to attach processed resumes to when --group-session is used",
    )

    parser.add_argument(
        "--group-session",
        action="store_true",
        help="Group all newly processed resumes into one RecruiterSession instead of the default one-session-per-resume workflow.",
    )

    parser.add_argument(
        "--candidate-type",
        dest="candidate_type",
        choices=["INTERNAL", "EXTERNAL"],
        default="EXTERNAL",
        help="Specify the candidate pool type for the ingested resumes.",
    )

    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Process infrastructure-failed and unprocessed files from the retry manifest.",
    )

    parser.add_argument(
        "--retry-manifest",
        default=str(RETRY_MANIFEST_FILE),
        help="Path to the retry manifest JSON file.",
    )

    return parser.parse_args()


# ---------------------------------------------------------------------
# Resume Discovery
# ---------------------------------------------------------------------

def discover_resumes(folder: Path):
    resumes = []

    for file in folder.rglob("*"):
        if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
            resumes.append(file)

    return sorted(resumes)


# ---------------------------------------------------------------------
# CSV Report
# ---------------------------------------------------------------------

def initialize_report():

    with open(REPORT_FILE, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "Resume Name",
                "Status",
                "Resume UUID",
                "Processing Time (s)",
                "Error",
            ]
        )


def append_report(name, status, resume_id="", elapsed="", error=""):

    with open(REPORT_FILE, "a", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                name,
                status,
                resume_id,
                elapsed,
                error,
            ]
        )


def load_retry_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read retry manifest %s", path)
        return []
    entries = payload.get("entries", []) if isinstance(payload, dict) else payload
    return entries if isinstance(entries, list) else []


def write_retry_manifest(path: Path, entries: list[dict]) -> None:
    existing = load_retry_manifest(path)
    merged: dict[str, dict] = {}
    for entry in [*existing, *entries]:
        file_path = str(entry.get("file_path") or "").strip()
        if not file_path:
            continue
        merged[file_path] = {
            "file_path": file_path,
            "file_name": entry.get("file_name") or Path(file_path).name,
            "failure_type": entry.get("failure_type") or STATUS_INFRASTRUCTURE_FAILED,
            "error_summary": str(entry.get("error_summary") or "")[:300],
            "attempts": int(entry.get("attempts") or 0),
            "timestamp": entry.get("timestamp") or utc_now(),
        }

    payload = {"updated_at": utc_now(), "entries": list(merged.values())}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def remove_retry_manifest_entries(path: Path, completed_paths: set[str]) -> None:
    if not completed_paths:
        return
    entries = [
        entry
        for entry in load_retry_manifest(path)
        if str(entry.get("file_path") or "") not in completed_paths
    ]
    payload = {"updated_at": utc_now(), "entries": entries}
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def manifest_entry(resume: Path, failure_type: str, error: str = "", attempts: int = 0) -> dict:
    return {
        "file_path": str(resume.resolve()),
        "file_name": resume.name,
        "failure_type": failure_type,
        "error_summary": str(error)[:300],
        "attempts": attempts,
        "timestamp": utc_now(),
    }


def resumes_from_manifest(path: Path):
    resumes: list[Path] = []
    missing: list[dict] = []
    for entry in load_retry_manifest(path):
        if entry.get("failure_type") not in {STATUS_INFRASTRUCTURE_FAILED, STATUS_UNPROCESSED}:
            continue
        file_path = Path(str(entry.get("file_path") or ""))
        if file_path.exists() and file_path.is_file():
            resumes.append(file_path)
        else:
            missing.append(entry)
    return sorted(dict.fromkeys(resumes)), missing


def wait_for_database_recovery(
    *,
    processed_count: int,
    total: int,
    failed: int,
    duplicates: int,
    infrastructure_failed: int,
    unprocessed: int,
    duplicate_warnings: list[dict],
) -> bool:
    for attempt in range(1, DB_RECOVERY_CHECKS + 1):
        update_bulk_progress(
            processed=processed_count,
            total=total,
            failed=failed,
            duplicates=duplicates,
            infrastructure_failed=infrastructure_failed,
            pending_retry=infrastructure_failed + unprocessed,
            unprocessed=unprocessed,
            duplicate_warnings=duplicate_warnings,
            current_file="",
            message=f"Bulk import temporarily paused. Waiting for database connection ({attempt}/{DB_RECOVERY_CHECKS}).",
        )
        logger.warning("Database recovery check %s/%s.", attempt, DB_RECOVERY_CHECKS)
        if database_health_check():
            update_bulk_progress(
                processed=processed_count,
                total=total,
                failed=failed,
                duplicates=duplicates,
                infrastructure_failed=infrastructure_failed,
                pending_retry=infrastructure_failed + unprocessed,
                unprocessed=unprocessed,
                duplicate_warnings=duplicate_warnings,
                current_file="",
                message="Database connection restored. Resuming bulk import.",
            )
            return True
        time.sleep(DB_RECOVERY_DELAY_SECONDS)
    return False



# Resume Processing
# ---------------------------------------------------------------------

def process_resumes(
    resumes,
    session_id=None,
    group_session=False,
    candidate_type="EXTERNAL",
    retry_manifest_path: Path = RETRY_MANIFEST_FILE,
):

    initialize_report()

    total = len(resumes)

    processed = 0
    failed = 0
    duplicates = 0
    infrastructure_failed = 0
    unprocessed = 0
    consecutive_infra_failures = 0
    stopped_reason = ""
    pending_manifest_entries: list[dict] = []
    completed_retry_paths: set[str] = set()
    duplicate_warnings = []

    overall_start = time.time()
    start_bulk_import(total)
    if not database_health_check():
        entries = [
            manifest_entry(
                resume,
                STATUS_UNPROCESSED,
                "Bulk import did not start because the database was unavailable.",
                0,
            )
            for resume in resumes
        ]
        write_retry_manifest(retry_manifest_path, entries)
        update_bulk_progress(
            processed=0,
            total=total,
            failed=0,
            duplicates=0,
            infrastructure_failed=0,
            pending_retry=len(resumes),
            unprocessed=len(resumes),
            duplicate_warnings=[],
            current_file="",
            message="Bulk import paused because the database is unavailable.",
        )
        mark_bulk_import_interrupted(
            "Bulk import paused because the database is unavailable. Resumes are available for retry."
        )
        print("\nDatabase is unavailable. No resumes were processed.")
        print(f"Retry manifest: {retry_manifest_path}")
        return

    if group_session and session_id:
        active_session_id = session_id
    elif group_session:
        active_session_id = document_service.create_session(
            title=f"Bulk Processing {datetime_label()}"
        ).session_id
    else:
        active_session_id = None

    print("\nProcessing resumes...\n")
    print(
        f"Session: {active_session_id if active_session_id else 'one persistent session per unique resume'}\n"
    )

    try:
        for index, resume in enumerate(tqdm(
            resumes,
            desc="Processing",
            unit="resume",
        )):

            start = time.time()
            update_bulk_progress(
                processed=processed + failed + duplicates + infrastructure_failed,
                total=total,
                failed=failed,
                duplicates=duplicates,
                infrastructure_failed=infrastructure_failed,
                pending_retry=infrastructure_failed + unprocessed,
                unprocessed=unprocessed,
                duplicate_warnings=duplicate_warnings,
                current_file=resume.name,
                message=f"Processing {resume.name}",
            )

            try:

                session = document_service.add_document(
                    file_path=resume,
                    display_name=resume.name,
                    session_id=active_session_id if group_session else None,
                    bulk_mode=True,
                )

                document = session.document

                resume_id = document.get("resume_id", "")

                if resume_id:
                    from database.crud import update_resume_candidate_type
                    retry_database_operation(
                        lambda: update_resume_candidate_type(resume_id, candidate_type),
                        filename=resume.name,
                        operation_name="candidate type update",
                    )

                elapsed = round(time.time() - start, 2)

                processed += 1
                consecutive_infra_failures = 0
                completed_retry_paths.add(str(resume.resolve()))

                append_report(
                    resume.name,
                    "Success",
                    resume_id,
                    elapsed,
                    "",
                )

                logger.info(
                    "%s processed successfully (%s)",
                    resume.name,
                    resume_id,
                )
                update_bulk_progress(
                    processed=processed + failed + duplicates + infrastructure_failed,
                    total=total,
                    failed=failed,
                    duplicates=duplicates,
                    infrastructure_failed=infrastructure_failed,
                    pending_retry=infrastructure_failed + unprocessed,
                    unprocessed=unprocessed,
                    duplicate_warnings=duplicate_warnings,
                    current_file="",
                    last_completed_file=resume.name,
                    message=f"Processed {resume.name}",
                )

            except DuplicateCandidateError as e:

                elapsed = round(time.time() - start, 2)

                duplicates += 1
                consecutive_infra_failures = 0
                completed_retry_paths.add(str(resume.resolve()))

                candidate_name = e.payload.get("candidate_name") or "Unknown"
                email = e.payload.get("email") or "Unknown"
                phone = e.payload.get("phone") or "Unknown"
                reason = e.payload.get("reason") or "Duplicate candidate matching criteria"

                warning_info = {
                    "file_name": resume.name,
                    "candidate_name": candidate_name,
                    "email": email,
                    "phone": phone,
                    "reason": reason,
                    "timestamp": utc_now(),
                }
                duplicate_warnings.append(warning_info)

                append_report(
                    resume.name,
                    "Skipped (Duplicate)",
                    e.payload.get("existing_resume_id", ""),
                    elapsed,
                    f"Duplicate: {reason}",
                )

                logger.warning(
                    "%s skipped as duplicate (%s - %s)",
                    resume.name,
                    candidate_name,
                    reason,
                )
                update_bulk_progress(
                    processed=processed + failed + duplicates + infrastructure_failed,
                    total=total,
                    failed=failed,
                    duplicates=duplicates,
                    infrastructure_failed=infrastructure_failed,
                    pending_retry=infrastructure_failed + unprocessed,
                    unprocessed=unprocessed,
                    duplicate_warnings=duplicate_warnings,
                    current_file="",
                    last_completed_file=resume.name,
                    message=f"Skipped duplicate {resume.name}",
                )

            except InfrastructureError as e:
                elapsed = round(time.time() - start, 2)
                infrastructure_failed += 1
                consecutive_infra_failures += 1
                pending_manifest_entries.append(
                    manifest_entry(
                        resume,
                        STATUS_INFRASTRUCTURE_FAILED,
                        str(e),
                        getattr(e, "attempts", 0),
                    )
                )

                append_report(
                    resume.name,
                    STATUS_INFRASTRUCTURE_FAILED,
                    "",
                    elapsed,
                    str(e),
                )

                logger.error(
                    "%s failed due to infrastructure outage after %s attempt(s).",
                    resume.name,
                    getattr(e, "attempts", 0),
                )
                update_bulk_progress(
                    processed=processed + failed + duplicates + infrastructure_failed,
                    total=total,
                    failed=failed,
                    duplicates=duplicates,
                    infrastructure_failed=infrastructure_failed,
                    pending_retry=infrastructure_failed + unprocessed,
                    unprocessed=unprocessed,
                    duplicate_warnings=duplicate_warnings,
                    current_file="",
                    last_completed_file=resume.name,
                    message=f"Database connection interrupted while processing {resume.name}.",
                )

                if consecutive_infra_failures >= MAX_CONSECUTIVE_INFRA_FAILURES:
                    recovered = wait_for_database_recovery(
                        processed_count=processed + failed + duplicates + infrastructure_failed,
                        total=total,
                        failed=failed,
                        duplicates=duplicates,
                        infrastructure_failed=infrastructure_failed,
                        unprocessed=unprocessed,
                        duplicate_warnings=duplicate_warnings,
                    )
                    if recovered:
                        consecutive_infra_failures = 0
                        continue

                    remaining = resumes[index + 1 :]
                    unprocessed = len(remaining)
                    pending_manifest_entries.extend(
                        manifest_entry(
                            remaining_resume,
                            STATUS_UNPROCESSED,
                            "Bulk import stopped because the database remained unavailable.",
                            0,
                        )
                        for remaining_resume in remaining
                    )
                    stopped_reason = "Database unavailable"
                    write_retry_manifest(retry_manifest_path, pending_manifest_entries)
                    update_bulk_progress(
                        processed=processed + failed + duplicates + infrastructure_failed,
                        total=total,
                        failed=failed,
                        duplicates=duplicates,
                        infrastructure_failed=infrastructure_failed,
                        pending_retry=infrastructure_failed + unprocessed,
                        unprocessed=unprocessed,
                        duplicate_warnings=duplicate_warnings,
                        current_file="",
                        message="Bulk import paused due to database connectivity.",
                    )
                    mark_bulk_import_interrupted(
                        "Bulk import paused due to database connectivity. Remaining resumes are available for retry."
                    )
                    logger.error(
                        "Circuit breaker stopped bulk import after %s consecutive infrastructure failures.",
                        consecutive_infra_failures,
                    )
                    break

            except Exception as e:

                elapsed = round(time.time() - start, 2)

                failed += 1
                consecutive_infra_failures = 0

                append_report(
                    resume.name,
                    "Failed",
                    "",
                    elapsed,
                    str(e),
                )

                logger.exception(
                    "Failed processing %s",
                    resume.name,
                )
                update_bulk_progress(
                    processed=processed + failed + duplicates + infrastructure_failed,
                    total=total,
                    failed=failed,
                    duplicates=duplicates,
                    infrastructure_failed=infrastructure_failed,
                    pending_retry=infrastructure_failed + unprocessed,
                    unprocessed=unprocessed,
                    duplicate_warnings=duplicate_warnings,
                    current_file="",
                    last_completed_file=resume.name,
                    message=f"Failed {resume.name}",
                )
    except KeyboardInterrupt:
        logger.error("Bulk processing interrupted by user (KeyboardInterrupt).")
        mark_bulk_import_interrupted("Bulk import was interrupted by user (KeyboardInterrupt).")
        print("\n\nBulk processing interrupted by user.")
        raise
    except Exception as e:
        logger.exception("Bulk processing failed unexpectedly.")
        mark_bulk_import_interrupted(f"Bulk import failed unexpectedly: {e}")
        print(f"\n\nBulk processing failed unexpectedly: {e}")
        raise

    if pending_manifest_entries:
        write_retry_manifest(retry_manifest_path, pending_manifest_entries)
    remove_retry_manifest_entries(retry_manifest_path, completed_retry_paths)

    total_time = time.time() - overall_start

    average = total_time / total if total else 0

    success_rate = (processed / total) * 100 if total else 0
    pending_retry = infrastructure_failed + unprocessed

    print("\n" + "=" * 65)
    print("Bulk Processing Summary")
    print("=" * 65)

    print(f"Total Resumes      : {total}")
    print(f"Successfully Added : {processed}")
    print(f"Duplicates Skipped : {duplicates}")
    print(f"Document Failed    : {failed}")
    print(f"Infrastructure Fail: {infrastructure_failed}")
    print(f"Pending Retry      : {pending_retry}")
    print(f"Unprocessed        : {unprocessed}")
    if stopped_reason:
        print(f"Stopped Reason     : {stopped_reason}")
    print(f"Success Rate       : {success_rate:.2f}%")
    print(f"Total Time         : {total_time:.2f} seconds")
    print(f"Average / Resume   : {average:.2f} seconds")

    print(f"\nCSV Report : {REPORT_FILE}")
    print(f"Log File   : {LOG_FILE}")
    print(f"Session    : {active_session_id if active_session_id else 'one per unique resume'}")
    if not stopped_reason:
        finish_bulk_import(
            processed=processed + failed + duplicates + infrastructure_failed,
            total=total,
            failed=failed,
            duplicates=duplicates,
            infrastructure_failed=infrastructure_failed,
            pending_retry=pending_retry,
            unprocessed=unprocessed,
        )


def datetime_label():
    return time.strftime("%Y-%m-%d %H:%M:%S")
# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    args = parse_arguments()

    retry_manifest_path = Path(args.retry_manifest)

    if args.retry_failed:
        resumes, missing = resumes_from_manifest(retry_manifest_path)
        if missing:
            logger.warning("Retry manifest contains %s missing file(s).", len(missing))
            print(f"\nSkipped {len(missing)} retry entries because the files were not found.")
        if not resumes:
            print(f"\nNo retryable resumes found in {retry_manifest_path}.")
            return
        print("=" * 65)
        print("Resume Intelligence Platform")
        print("Bulk Resume Retry Utility")
        print("=" * 65)
        print(f"\nRetry manifest:\n{retry_manifest_path}\n")
        print(f"Found {len(resumes)} retryable resume(s).\n")
        process_resumes(
            resumes,
            session_id=args.session_id,
            group_session=args.group_session,
            candidate_type=getattr(args, "candidate_type", "EXTERNAL"),
            retry_manifest_path=retry_manifest_path,
        )
        return

    if not args.folder:
        print("\nFolder is required unless --retry-failed is used.")
        return

    folder = Path(args.folder)

    if not folder.exists():

        print(f"\nFolder does not exist:\n{folder}")

        return

    if not folder.is_dir():

        print("\nProvided path is not a directory.")

        return

    print("=" * 65)
    print("Resume Intelligence Platform")
    print("Bulk Resume Processing Utility")
    print("=" * 65)

    print(f"\nScanning:\n{folder}\n")

    resumes = discover_resumes(folder)

    print(f"Found {len(resumes)} supported resume(s).\n")

    if not resumes:

        print("No PDF or DOCX files found.")

        return

    process_resumes(
        resumes,
        session_id=args.session_id,
        group_session=args.group_session,
        candidate_type=getattr(args, "candidate_type", "EXTERNAL"),
        retry_manifest_path=retry_manifest_path,
    )


if __name__ == "__main__":
    main()
