from __future__ import annotations

from uuid import UUID

from database.crud import (
    create_session,
    ensure_default_session,
    ensure_one_session_per_resume,
    ensure_resume_session,
    get_active_session,
    list_resumes_by_session,
    list_sessions,
    set_active_session,
)


def ensure_session(session_id: str | UUID | None = None, title: str = "Resume Session"):
    if session_id:
        existing = set_active_session(session_id)
        if existing:
            return existing
        raise ValueError("Resume session was not found.")

    return create_session(title=title, active=True)


def ensure_active_or_default_session():
    active = get_active_session()
    return active or ensure_default_session()


def ensure_resume_workspace(resume, active: bool = False):
    title = resume.candidate_name or resume.original_file_name
    return ensure_resume_session(resume.id, title=title, active=active)


def backfill_resume_workspaces():
    return ensure_one_session_per_resume()


def create_persistent_session(title: str = "Resume Session"):
    return create_session(title=title or "Resume Session", active=True)


def activate_persistent_session(session_id: str | UUID):
    session = set_active_session(session_id)
    if not session:
        raise ValueError("Resume session was not found.")
    return session


def public_session(session, active_session_id: str | UUID | None = None) -> dict:
    resumes = list_resumes_by_session(session.id)
    active_id = str(active_session_id) if active_session_id else None
    document = _public_resume_document(resumes[0]) if resumes else None
    resume = resumes[0] if resumes else None

    return {
        "session_id": str(session.id),
        "id": str(session.id),
        "title": session.title,
        "display_name": session.title,
        "candidate_name": resume.candidate_name if resume else None,
        "original_file_name": resume.original_file_name if resume else None,
        "resume_id": str(resume.id) if resume else None,
        "uploaded_at": resume.uploaded_at if resume else session.created_at,
        "hr_decision": resume.hr_decision if resume else "PENDING",
        "decision_at": resume.decision_at if resume else None,
        "document": document,
        "documents": [_public_resume_document(resume) for resume in resumes],
        "document_count": len(resumes),
        "message_count": len(session.chat_history or []),
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "last_accessed": session.last_accessed,
        "is_active": str(session.id) == active_id,
        "active": session.active,
    }


def public_sessions() -> list[dict]:
    ensure_one_session_per_resume()
    active = get_active_session()
    active_id = active.id if active else None
    return [
        public_session(session, active_id)
        for session in list_sessions()
    ]


def public_resumes_for_session(session_id: str | UUID) -> list[dict]:
    return [
        _public_resume(resume)
        for resume in list_resumes_by_session(session_id)
    ]


def _public_resume_document(resume) -> dict:
    return {
        "document_id": str(resume.id),
        "resume_id": str(resume.id),
        "name": resume.original_file_name,
        "preview": "",
        "page_count": None,
        "character_count": 0,
        "chunk_count": 0,
        "indexed_at": resume.uploaded_at,
        "metadata": _metadata_from_resume(resume),
        "extraction_method": None,
        "extraction_quality": {},
    }


def _public_resume(resume) -> dict:
    return {
        "id": str(resume.id),
        "session_id": str(resume.session_id) if resume.session_id else None,
        "original_file_name": resume.original_file_name,
        "candidate_name": resume.candidate_name,
        "email": resume.email,
        "phone_number": resume.phone_number,
        "skills": resume.skills or [],
        "cities": resume.cities or [],
        "fresher": resume.fresher,
        "processing_status": resume.processing_status,
        "is_verified": resume.is_verified,
        "extraction_status": resume.extraction_status,
        "notes": resume.notes,
        "hr_notes": resume.hr_notes,
        "technical_notes": resume.technical_notes,
        "final_notes": resume.final_notes,
        "hr_decision": resume.hr_decision,
        "decision_at": resume.decision_at,
        "uploaded_at": resume.uploaded_at,
        "updated_at": resume.updated_at,
    }


def _metadata_from_resume(resume) -> dict:
    return {
        "Resume File Name": resume.original_file_name,
        "Candidate Name": resume.candidate_name or "",
        "Email": resume.email or "",
        "Phone Number": resume.phone_number or "",
        "Cities": resume.cities or [],
        "Skills": resume.skills or [],
        "Fresher": "Yes" if resume.fresher else "No",
        "HR Decision": resume.hr_decision,
    }
