from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError

from database.connection import engine


logger = logging.getLogger(__name__)

DB_RETRY_DELAYS = (2, 5, 10, 20)
DB_MAX_RETRIES = len(DB_RETRY_DELAYS)
TRANSIENT_DB_MARKERS = (
    "connection refused",
    "connection timed out",
    "connection timeout",
    "could not connect to server",
    "no route to host",
    "server closed the connection unexpectedly",
    "server unexpectedly closed connection",
    "connection reset",
    "terminating connection",
    "connection not open",
    "network is unreachable",
    "timeout expired",
)

T = TypeVar("T")


class InfrastructureError(RuntimeError):
    """Raised only for transient infrastructure failures during bulk import."""

    def __init__(self, message: str, *, attempts: int = 1, original: BaseException | None = None):
        super().__init__(message)
        self.attempts = attempts
        self.original = original


def is_transient_database_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current:
        if isinstance(current, OperationalError):
            return _contains_transient_marker(current)
        if isinstance(current, DBAPIError) and getattr(current, "connection_invalidated", False):
            return True
        current = current.__cause__ or current.__context__
    return False


def retry_database_operation(
    operation: Callable[[], T],
    *,
    filename: str,
    operation_name: str = "database operation",
) -> T:
    attempts = 1
    while True:
        try:
            return operation()
        except Exception as exc:
            if not is_transient_database_error(exc):
                raise

            if attempts > DB_MAX_RETRIES:
                raise InfrastructureError(
                    f"Database unavailable while processing {filename}.",
                    attempts=attempts,
                    original=exc,
                ) from exc

            delay = DB_RETRY_DELAYS[attempts - 1]
            logger.warning(
                "Database unavailable during %s for %s. Retry %s/%s in %s seconds.",
                operation_name,
                filename,
                attempts,
                DB_MAX_RETRIES,
                delay,
            )
            time.sleep(delay)
            attempts += 1


def database_health_check() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        if is_transient_database_error(exc):
            logger.warning("Database health check failed: %s", _safe_error_summary(exc))
            return False
        raise


def _contains_transient_marker(exc: BaseException) -> bool:
    message_parts = []
    current: BaseException | None = exc
    while current:
        message_parts.append(str(current))
        current = current.__cause__ or current.__context__

    message = " ".join(message_parts).lower()
    return any(marker in message for marker in TRANSIENT_DB_MARKERS)


def _safe_error_summary(exc: BaseException) -> str:
    message = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
    return message[:300]
