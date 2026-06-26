from pathlib import Path
from uuid import UUID
import hashlib
import mimetypes

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from backend.schemas.resume import ResumeListResponse, ResumeResponse, ResumeUpdate
from database.crud import (
    delete_resume,
    get_resume_download_by_id,
    get_resume_by_id,
    list_resumes,
    save_resume,
    update_resume_metadata,
)
from database.models import Resume


def _list_value(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if value is None:
        return []

    return [str(value).strip()] if str(value).strip() else []


def _fresher_value(value) -> bool:
    if isinstance(value, bool):
        return value

    return str(value or "").strip().lower() in {"yes", "true", "1", "fresher"}


def build_resume_payload(file_path: Path, original_file_name: str, metadata: dict) -> dict:
    file_bytes = file_path.read_bytes()
    mime_type = mimetypes.guess_type(original_file_name or file_path.name)[0]

    return {
        "resume_hash": hashlib.sha256(file_bytes).hexdigest(),
        "original_file_name": original_file_name or file_path.name,
        "stored_file_name": file_path.name,
        "file_path": str(file_path),
        "mime_type": mime_type or "application/octet-stream",
        "resume_blob": file_bytes,
        "candidate_name": metadata.get("Candidate Name") or None,
        "email": metadata.get("Email") or None,
        "phone_number": metadata.get("Phone Number") or None,
        "skills": _list_value(metadata.get("Skills")),
        "cities": _list_value(metadata.get("Cities")),
        "fresher": _fresher_value(metadata.get("Fresher")),
        "processing_status": "COMPLETED",
        "is_verified": False,
        "extraction_status": "SUCCESS",
        "notes": None,
    }


def persist_resume_metadata(file_path: Path, original_file_name: str, metadata: dict) -> Resume:
    return save_resume(build_resume_payload(file_path, original_file_name, metadata))


def list_resume_response() -> ResumeListResponse:
    resumes = list_resumes()
    return ResumeListResponse(total=len(resumes), resumes=resumes)


def get_resume_response(resume_id: UUID) -> Resume | None:
    return get_resume_by_id(resume_id)


def get_resume_download(resume_id: UUID):
    return get_resume_download_by_id(resume_id)


def update_resume_response(resume_id: UUID, payload: ResumeUpdate) -> Resume | None:
    data = payload.model_dump(exclude_unset=True)
    return update_resume_metadata(resume_id, data)


def delete_resume_response(resume_id: UUID) -> bool:
    return delete_resume(resume_id)


__all__ = [
    "IntegrityError",
    "ResumeResponse",
    "ResumeUpdate",
    "SQLAlchemyError",
    "delete_resume_response",
    "get_resume_response",
    "get_resume_download",
    "list_resume_response",
    "persist_resume_metadata",
    "update_resume_response",
]
