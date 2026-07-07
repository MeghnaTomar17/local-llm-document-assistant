from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


STATUS_PATH = Path("backend/runtime/bulk_import_status.json")


def default_bulk_status() -> dict[str, Any]:
    return {
        "running": False,
        "processed": 0,
        "total": 0,
        "failed": 0,
        "current_file": "",
        "last_completed_file": "",
        "message": "No bulk import is running.",
        "started_at": None,
        "updated_at": None,
        "finished_at": None,
    }


def read_bulk_status() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return default_bulk_status()

    try:
        with STATUS_PATH.open("r", encoding="utf-8") as file:
            return {**default_bulk_status(), **json.load(file)}
    except (OSError, json.JSONDecodeError):
        return {
            **default_bulk_status(),
            "message": "Import status is temporarily unavailable.",
            "updated_at": utc_now(),
        }


def write_bulk_status(**updates: Any) -> dict[str, Any]:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **read_bulk_status(),
        **updates,
        "updated_at": utc_now(),
    }

    with NamedTemporaryFile("w", encoding="utf-8", dir=STATUS_PATH.parent, delete=False) as file:
        json.dump(payload, file, indent=2)
        temp_path = Path(file.name)

    temp_path.replace(STATUS_PATH)
    return payload


def start_bulk_import(total: int) -> dict[str, Any]:
    now = utc_now()
    return write_bulk_status(
        running=True,
        processed=0,
        total=total,
        failed=0,
        current_file="",
        last_completed_file="",
        message="Bulk import is starting.",
        started_at=now,
        finished_at=None,
    )


def update_bulk_progress(
    *,
    processed: int,
    total: int,
    current_file: str = "",
    failed: int = 0,
    last_completed_file: str = "",
    message: str = "Bulk import is running.",
) -> dict[str, Any]:
    return write_bulk_status(
        running=True,
        processed=processed,
        total=total,
        failed=failed,
        current_file=current_file,
        last_completed_file=last_completed_file,
        message=message,
    )


def finish_bulk_import(*, processed: int, total: int, failed: int) -> dict[str, Any]:
    return write_bulk_status(
        running=False,
        processed=processed,
        total=total,
        failed=failed,
        current_file="",
        message=f"Bulk import finished. {processed} of {total} resumes processed.",
        finished_at=utc_now(),
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
