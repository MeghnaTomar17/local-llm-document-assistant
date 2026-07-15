from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PATH = Path("backend/runtime/bulk_import_status.json")

STATE_IDLE = "IDLE"
STATE_RUNNING = "RUNNING"
STATE_COMPLETED = "COMPLETED"
STATE_INTERRUPTED = "INTERRUPTED"


def default_bulk_status() -> dict[str, Any]:
    return {
        "state": STATE_IDLE,
        "running": False,
        "processed": 0,
        "total": 0,
        "failed": 0,
        "duplicates": 0,
        "infrastructure_failed": 0,
        "pending_retry": 0,
        "unprocessed": 0,
        "duplicate_warnings": [],
        "current_file": "",
        "last_completed_file": "",
        "message": "No bulk import is running.",
        "started_at": None,
        "updated_at": None,
        "finished_at": None,
        "interrupted": False,
        "interrupted_at": None,
        "pid": None,
    }


def read_bulk_status() -> dict[str, Any]:
    status = _read_status_file()
    if _is_running_state(status):
        pid = _coerce_pid(status.get("pid"))
        if pid and is_pid_running(pid):
            return _normalized_status(
                {
                    **status,
                    "state": STATE_RUNNING,
                    "running": True,
                    "interrupted": False,
                    "interrupted_at": None,
                }
            )

        interrupted_status = _normalized_status(
            {
                **status,
                "state": STATE_INTERRUPTED,
                "running": False,
                "interrupted": True,
                "interrupted_at": status.get("interrupted_at") or utc_now(),
                "message": "Bulk import was interrupted before completion.",
                "updated_at": utc_now(),
            }
        )
        _write_status_file(interrupted_status)
        return interrupted_status

    return _normalized_status(status)


def start_bulk_import(total: int, pid: int | None = None) -> dict[str, Any]:
    now = utc_now()
    return write_bulk_status(
        state=STATE_RUNNING,
        running=True,
        processed=0,
        total=total,
        failed=0,
        duplicates=0,
        infrastructure_failed=0,
        pending_retry=0,
        unprocessed=0,
        duplicate_warnings=[],
        current_file="",
        last_completed_file="",
        message="Bulk import is starting.",
        started_at=now,
        finished_at=None,
        interrupted=False,
        interrupted_at=None,
        pid=pid or os.getpid(),
    )


def update_bulk_progress(
    *,
    processed: int,
    total: int,
    current_file: str = "",
    failed: int = 0,
    duplicates: int = 0,
    infrastructure_failed: int = 0,
    pending_retry: int = 0,
    unprocessed: int = 0,
    duplicate_warnings: list[dict[str, Any]] | None = None,
    last_completed_file: str = "",
    message: str = "Bulk import is running.",
) -> dict[str, Any]:
    updates: dict[str, Any] = {
        "state": STATE_RUNNING,
        "running": True,
        "processed": processed,
        "total": total,
        "failed": failed,
        "duplicates": duplicates,
        "infrastructure_failed": infrastructure_failed,
        "pending_retry": pending_retry,
        "unprocessed": unprocessed,
        "current_file": current_file,
        "last_completed_file": last_completed_file,
        "message": message,
        "interrupted": False,
        "interrupted_at": None,
    }
    if duplicate_warnings is not None:
        updates["duplicate_warnings"] = duplicate_warnings
    return write_bulk_status(**updates)


def finish_bulk_import(
    *,
    processed: int,
    total: int,
    failed: int,
    duplicates: int = 0,
    infrastructure_failed: int = 0,
    pending_retry: int = 0,
    unprocessed: int = 0,
) -> dict[str, Any]:
    return write_bulk_status(
        state=STATE_COMPLETED,
        running=False,
        processed=processed,
        total=total,
        failed=failed,
        duplicates=duplicates,
        infrastructure_failed=infrastructure_failed,
        pending_retry=pending_retry,
        unprocessed=unprocessed,
        current_file="",
        message=f"Bulk import finished. {processed} of {total} resumes processed.",
        finished_at=utc_now(),
        interrupted=False,
        interrupted_at=None,
    )


def mark_bulk_import_interrupted(message: str = "Bulk import was interrupted.") -> dict[str, Any]:
    existing = _read_status_file()
    return write_bulk_status(
        state=STATE_INTERRUPTED,
        running=False,
        interrupted=True,
        interrupted_at=existing.get("interrupted_at") or utc_now(),
        message=message,
    )


def write_bulk_status(**updates: Any) -> dict[str, Any]:
    payload = _normalized_status(
        {
            **_read_status_file(),
            **updates,
            "updated_at": utc_now(),
        }
    )
    _write_status_file(payload)
    return payload


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        return _is_windows_pid_running(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_status_file() -> dict[str, Any]:
    if not STATUS_PATH.exists():
        return default_bulk_status()
    try:
        with STATUS_PATH.open("r", encoding="utf-8") as file:
            return _normalized_status(json.load(file))
    except (OSError, json.JSONDecodeError):
        return {
            **default_bulk_status(),
            "message": "Import status is temporarily unavailable.",
            "updated_at": utc_now(),
        }


def _write_status_file(payload: dict[str, Any]) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)

    with STATUS_PATH.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.flush()
        os.fsync(file.fileno())


def _normalized_status(status: dict[str, Any]) -> dict[str, Any]:
    explicit_state = status.get("state")
    payload = {**default_bulk_status(), **status}
    state = str(explicit_state or "").upper()

    if not state:
        if payload.get("interrupted"):
            state = STATE_INTERRUPTED
        elif payload.get("running"):
            state = STATE_RUNNING
        elif payload.get("finished_at"):
            state = STATE_COMPLETED
        else:
            state = STATE_IDLE

    if state not in {STATE_IDLE, STATE_RUNNING, STATE_COMPLETED, STATE_INTERRUPTED}:
        state = STATE_RUNNING if payload.get("running") else STATE_IDLE

    payload["state"] = state
    payload["running"] = state == STATE_RUNNING
    payload["interrupted"] = state == STATE_INTERRUPTED

    if state == STATE_RUNNING:
        payload["finished_at"] = None
        payload["interrupted_at"] = None
    elif state != STATE_INTERRUPTED:
        payload["interrupted_at"] = None

    return payload


def _is_running_state(status: dict[str, Any]) -> bool:
    return status.get("state") == STATE_RUNNING or bool(status.get("running"))


def _coerce_pid(value: Any) -> int | None:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return None
    return pid if pid > 0 else None


def _is_windows_pid_running(pid: int) -> bool:
    process_query_limited_information = 0x1000
    still_active = 259
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if not handle:
        return False

    exit_code = ctypes.wintypes.DWORD()
    try:
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return False
        return exit_code.value == still_active
    finally:
        kernel32.CloseHandle(handle)
