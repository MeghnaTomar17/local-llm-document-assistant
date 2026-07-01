from __future__ import annotations

import argparse
import csv
import logging
import time
from pathlib import Path

from tqdm import tqdm

from backend.services.document_service import document_service


SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

REPORT_FILE = "processing_report.csv"
LOG_FILE = "bulk_processing.log"


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


# ---------------------------------------------------------------------
# Resume Processing
# ---------------------------------------------------------------------

def process_resumes(resumes, session_id=None, group_session=False):

    initialize_report()

    total = len(resumes)

    processed = 0
    failed = 0

    overall_start = time.time()
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

    for resume in tqdm(
        resumes,
        desc="Processing",
        unit="resume",
    ):

        start = time.time()

        try:

            session = document_service.add_document(
                file_path=resume,
                display_name=resume.name,
                session_id=active_session_id if group_session else None,
            )

            document = session.document

            resume_id = document.get("resume_id", "")

            elapsed = round(time.time() - start, 2)

            processed += 1

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

        except Exception as e:

            elapsed = round(time.time() - start, 2)

            failed += 1

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

    total_time = time.time() - overall_start

    average = total_time / total if total else 0

    success_rate = (processed / total) * 100 if total else 0

    print("\n" + "=" * 65)
    print("Bulk Processing Summary")
    print("=" * 65)

    print(f"Total Resumes      : {total}")
    print(f"Successfully Added : {processed}")
    print(f"Failed             : {failed}")
    print(f"Success Rate       : {success_rate:.2f}%")
    print(f"Total Time         : {total_time:.2f} seconds")
    print(f"Average / Resume   : {average:.2f} seconds")

    print(f"\nCSV Report : {REPORT_FILE}")
    print(f"Log File   : {LOG_FILE}")
    print(f"Session    : {active_session_id if active_session_id else 'one per unique resume'}")


def datetime_label():
    return time.strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():

    args = parse_arguments()

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
    )


if __name__ == "__main__":
    main()
