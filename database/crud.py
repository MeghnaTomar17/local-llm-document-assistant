from datetime import datetime, timezone

from database.connection import SessionLocal
from database.models import RecruiterSearchHistory, RecruiterSession, Resume, ResumeChunk
from sqlalchemy import select, update


EDITABLE_RESUME_FIELDS = {
    "candidate_name",
    "email",
    "phone_number",
    "skills",
    "cities",
    "fresher",
    "hr_notes",
    "technical_notes",
    "final_notes",
    "hr_decision",
}

HR_DECISIONS = {"PENDING", "ON_HOLD", "ACCEPTED", "REJECTED"}


def create_resume(data: dict):

    session = SessionLocal()

    try:

        resume = Resume(**data)

        session.add(resume)

        session.commit()

        session.refresh(resume)

        return resume

    finally:

        session.close()

def get_resume_by_hash(resume_hash: str):

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.resume_hash == resume_hash
        )

        result = session.execute(statement)

        return result.scalar_one_or_none()

    finally:

        session.close()

def save_resume(data: dict):

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.resume_hash == data["resume_hash"]
        )

        existing = session.execute(statement).scalar_one_or_none()

        if existing:
            # Duplicate uploads must not overwrite recruiter edits, verification
            # state, or the already-linked persistent workspace.
            if not existing.resume_blob and data.get("resume_blob"):
                existing.resume_blob = data["resume_blob"]

            if not existing.session_id and data.get("session_id"):
                existing.session_id = data["session_id"]

            session.commit()
            session.refresh(existing)

            return existing

        # Resume not found → create new
        resume = Resume(**data)

        session.add(resume)

        session.commit()

        session.refresh(resume)

        return resume

    finally:

        session.close()

def get_resume_by_id(resume_id):

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.id == resume_id
        )

        return session.execute(
            statement
        ).scalar_one_or_none()

    finally:

        session.close()


def normalize_email(value: str | None) -> str:
    return str(value or "").strip().lower()


def normalize_name(value: str | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_phone(value: str | None) -> str:
    return "".join(char for char in str(value or "") if char.isdigit())


def find_duplicate_candidate(candidate_name: str | None, email: str | None, phone_number: str | None):

    normalized_name = normalize_name(candidate_name)
    normalized_email = normalize_email(email)
    normalized_phone = normalize_phone(phone_number)

    if not normalized_email and not normalized_phone:
        return None

    session = SessionLocal()

    try:

        candidates = session.execute(
            select(Resume).where(
                (Resume.email.is_not(None)) | (Resume.phone_number.is_not(None))
            )
        ).scalars().all()

        for resume in candidates:
            existing_name = normalize_name(resume.candidate_name)
            existing_email = normalize_email(resume.email)
            existing_phone = normalize_phone(resume.phone_number)

            same_email = normalized_email and existing_email == normalized_email
            same_phone = normalized_phone and existing_phone == normalized_phone
            same_name_email = normalized_name and same_email and existing_name == normalized_name
            same_name_phone = normalized_name and same_phone and existing_name == normalized_name

            if same_email or same_phone or same_name_email or same_name_phone:
                return resume

        return None

    finally:

        session.close()


def create_session(title: str = "Resume Session", active: bool = False):

    session = SessionLocal()

    try:

        if active:
            session.execute(
                update(RecruiterSession).values(active=False)
            )

        recruiter_session = RecruiterSession(
            title=title,
            active=active,
            last_accessed=datetime.now(timezone.utc),
        )

        session.add(recruiter_session)
        session.commit()
        session.refresh(recruiter_session)

        return recruiter_session

    finally:

        session.close()


def update_session_title(session_id, title: str):

    session = SessionLocal()

    try:

        recruiter_session = session.execute(
            select(RecruiterSession).where(
                RecruiterSession.id == session_id
            )
        ).scalar_one_or_none()

        if not recruiter_session:
            return None

        recruiter_session.title = title or recruiter_session.title
        recruiter_session.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(recruiter_session)

        return recruiter_session

    finally:

        session.close()


def ensure_resume_session(resume_id, title: str | None = None, active: bool = False):

    session = SessionLocal()

    try:

        resume = session.execute(
            select(Resume).where(
                Resume.id == resume_id
            )
        ).scalar_one_or_none()

        if not resume:
            return None

        session_title = title or resume.candidate_name or resume.original_file_name

        if resume.session_id:
            sibling_count = session.execute(
                select(Resume).where(
                    Resume.session_id == resume.session_id
                )
            ).scalars().all()

            if len(sibling_count) > 1:
                resume.session_id = None
                session.flush()
            else:
                recruiter_session = session.execute(
                    select(RecruiterSession).where(
                        RecruiterSession.id == resume.session_id
                    )
                ).scalar_one_or_none()

                if recruiter_session:
                    recruiter_session.title = session_title
                    recruiter_session.updated_at = datetime.now(timezone.utc)
                    if active:
                        session.execute(
                            update(RecruiterSession).values(active=False)
                        )
                        recruiter_session.active = True
                        recruiter_session.last_accessed = datetime.now(timezone.utc)

                    session.commit()
                    session.refresh(recruiter_session)

                    return recruiter_session

        if resume.session_id:
            recruiter_session = session.execute(
                select(RecruiterSession).where(
                    RecruiterSession.id == resume.session_id
                )
            ).scalar_one_or_none()

            if recruiter_session:
                recruiter_session.title = session_title
                recruiter_session.updated_at = datetime.now(timezone.utc)
                if active:
                    session.execute(
                        update(RecruiterSession).values(active=False)
                    )
                    recruiter_session.active = True
                    recruiter_session.last_accessed = datetime.now(timezone.utc)

                session.commit()
                session.refresh(recruiter_session)

                return recruiter_session

        if active:
            session.execute(
                update(RecruiterSession).values(active=False)
            )

        recruiter_session = RecruiterSession(
            title=session_title,
            active=active,
            last_accessed=datetime.now(timezone.utc),
        )

        session.add(recruiter_session)
        session.flush()

        resume.session_id = recruiter_session.id
        resume.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(recruiter_session)

        return recruiter_session

    finally:

        session.close()


def get_session_by_id(session_id):

    session = SessionLocal()

    try:

        statement = select(RecruiterSession).where(
            RecruiterSession.id == session_id
        )

        return session.execute(
            statement
        ).scalar_one_or_none()

    finally:

        session.close()


def list_sessions():

    session = SessionLocal()

    try:

        statement = select(RecruiterSession).join(
            Resume,
            Resume.session_id == RecruiterSession.id,
        ).group_by(
            RecruiterSession.id
        ).order_by(
            RecruiterSession.updated_at.desc()
        )

        return session.execute(
            statement
        ).scalars().all()

    finally:

        session.close()


def set_active_session(session_id):

    session = SessionLocal()

    try:

        statement = select(RecruiterSession).where(
            RecruiterSession.id == session_id
        )

        recruiter_session = session.execute(
            statement
        ).scalar_one_or_none()

        if not recruiter_session:
            return None

        session.execute(
            update(RecruiterSession).values(active=False)
        )

        recruiter_session.active = True
        recruiter_session.last_accessed = datetime.now(timezone.utc)
        recruiter_session.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(recruiter_session)

        return recruiter_session

    finally:

        session.close()


def update_session_chat_history(session_id, messages: list[dict]):

    session = SessionLocal()

    try:

        recruiter_session = session.execute(
            select(RecruiterSession).where(
                RecruiterSession.id == session_id
            )
        ).scalar_one_or_none()

        if not recruiter_session:
            return None

        recruiter_session.chat_history = messages
        recruiter_session.updated_at = datetime.now(timezone.utc)
        recruiter_session.last_accessed = datetime.now(timezone.utc)

        session.commit()
        session.refresh(recruiter_session)

        return recruiter_session

    finally:

        session.close()


def get_active_session():

    session = SessionLocal()

    try:

        statement = select(RecruiterSession).where(
            RecruiterSession.active == True
        )

        return session.execute(
            statement
        ).scalars().first()

    finally:

        session.close()


def ensure_default_session():

    session = SessionLocal()

    try:

        existing = session.execute(
            select(RecruiterSession).order_by(RecruiterSession.created_at.asc())
        ).scalars().first()

        if existing:
            default_session = existing
        else:
            default_session = RecruiterSession(
                title="Default Session",
                active=True,
                last_accessed=datetime.now(timezone.utc),
            )
            session.add(default_session)
            session.flush()

        session.execute(
            update(Resume)
            .where(Resume.session_id.is_(None))
            .values(session_id=default_session.id)
        )

        session.commit()
        session.refresh(default_session)

        return default_session

    finally:

        session.close()


def ensure_one_session_per_resume():

    session = SessionLocal()

    try:

        resumes = session.execute(
            select(Resume).order_by(
                Resume.uploaded_at.asc(),
                Resume.id.asc(),
            )
        ).scalars().all()

        canonical_by_hash = {}
        duplicate_resume_ids = []

        for resume in resumes:

            canonical = canonical_by_hash.get(resume.resume_hash)

            if canonical:
                if not canonical.session_id and resume.session_id:
                    canonical.session_id = resume.session_id
                duplicate_resume_ids.append(str(resume.id))
                continue

            canonical_by_hash[resume.resume_hash] = resume
            session_title = resume.candidate_name or resume.original_file_name

            if resume.session_id:
                session_resumes = session.execute(
                    select(Resume).where(
                        Resume.session_id == resume.session_id
                    )
                ).scalars().all()

                if len(session_resumes) > 1:
                    resume.session_id = None
                    session.flush()
                else:
                    recruiter_session = session.execute(
                        select(RecruiterSession).where(
                            RecruiterSession.id == resume.session_id
                        )
                    ).scalar_one_or_none()

                    if recruiter_session:
                        recruiter_session.title = session_title
                        recruiter_session.updated_at = datetime.now(timezone.utc)
                        continue

            if resume.session_id:
                recruiter_session = session.execute(
                    select(RecruiterSession).where(
                        RecruiterSession.id == resume.session_id
                    )
                ).scalar_one_or_none()

                if recruiter_session:
                    recruiter_session.title = session_title
                    recruiter_session.updated_at = datetime.now(timezone.utc)
                    continue

            recruiter_session = RecruiterSession(
                title=session_title,
                active=False,
                last_accessed=datetime.now(timezone.utc),
            )

            session.add(recruiter_session)
            session.flush()

            resume.session_id = recruiter_session.id
            resume.updated_at = datetime.now(timezone.utc)

        session.commit()

        return {
            "sessions_ensured": len(canonical_by_hash),
            "duplicate_resume_ids": duplicate_resume_ids,
        }

    finally:

        session.close()


def get_resume_download_by_id(resume_id):

    session = SessionLocal()

    try:

        statement = select(
            Resume.original_file_name,
            Resume.mime_type,
            Resume.resume_blob,
        ).where(
            Resume.id == resume_id
        )

        return session.execute(
            statement
        ).one_or_none()

    finally:

        session.close()

def list_resumes():

    session = SessionLocal()

    try:

        statement = select(Resume)

        return session.execute(
            statement
        ).scalars().all()

    finally:

        session.close()


def list_resumes_by_session(session_id):

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.session_id == session_id
        ).order_by(
            Resume.uploaded_at.desc()
        )

        return session.execute(
            statement
        ).scalars().all()

    finally:

        session.close()


def update_resume_metadata(resume_id, data: dict):

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.id == resume_id
        )

        resume = session.execute(
            statement
        ).scalar_one_or_none()

        if not resume:
            return None

        for key, value in data.items():

            if key in EDITABLE_RESUME_FIELDS:
                if key == "hr_decision":
                    value = str(value or "PENDING").upper()
                    if value not in HR_DECISIONS:
                        continue
                    if resume.hr_decision != value:
                        resume.decision_at = (
                            None if value == "PENDING" else datetime.now(timezone.utc)
                        )
                setattr(resume, key, value)

        resume.is_verified = True
        resume.updated_at = datetime.now(timezone.utc)

        if "candidate_name" in data and resume.session_id:
            recruiter_session = session.execute(
                select(RecruiterSession).where(
                    RecruiterSession.id == resume.session_id
                )
            ).scalar_one_or_none()

            if recruiter_session:
                recruiter_session.title = resume.candidate_name or resume.original_file_name
                recruiter_session.updated_at = datetime.now(timezone.utc)

        session.commit()
        session.refresh(resume)

        return resume

    finally:

        session.close()


def delete_resume(resume_id) -> bool:

    session = SessionLocal()

    try:

        statement = select(Resume).where(
            Resume.id == resume_id
        )

        resume = session.execute(
            statement
        ).scalar_one_or_none()

        if not resume:
            return False

        session.delete(resume)
        session.commit()

        return True

    finally:

        session.close()


def delete_resume_chunks(resume_id) -> int:

    session = SessionLocal()

    try:

        chunks = session.execute(
            select(ResumeChunk).where(
                ResumeChunk.resume_id == resume_id
            )
        ).scalars().all()

        count = len(chunks)
        for chunk in chunks:
            session.delete(chunk)

        session.commit()

        return count

    finally:

        session.close()


def save_resume_chunks(resume_id, chunks: list[dict]):

    session = SessionLocal()

    try:

        existing_chunks = session.execute(
            select(ResumeChunk).where(
                ResumeChunk.resume_id == resume_id
            )
        ).scalars().all()

        for chunk in existing_chunks:
            session.delete(chunk)

        session.flush()

        saved_chunks = []
        seen_chunk_indexes = set()
        for index, chunk in enumerate(chunks, start=1):
            chunk_index = int(chunk.get("chunk_number") or chunk.get("chunk_index") or index)
            if chunk_index in seen_chunk_indexes:
                continue
            seen_chunk_indexes.add(chunk_index)

            resume_chunk = ResumeChunk(
                resume_id=resume_id,
                chunk_index=chunk_index,
                section=chunk.get("section"),
                title=chunk.get("title"),
                page_number=chunk.get("page") or chunk.get("page_number"),
                content=chunk.get("content") or chunk.get("text") or "",
            )
            if not resume_chunk.content:
                continue
            session.add(resume_chunk)
            saved_chunks.append(resume_chunk)

        session.commit()

        for chunk in saved_chunks:
            session.refresh(chunk)

        return saved_chunks

    finally:

        session.close()


def get_resume_chunks(resume_id):

    session = SessionLocal()

    try:

        statement = select(ResumeChunk).where(
            ResumeChunk.resume_id == resume_id
        ).order_by(
            ResumeChunk.chunk_index.asc()
        )

        return session.execute(statement).scalars().all()

    finally:

        session.close()


def create_search_history(data: dict):

    session = SessionLocal()

    try:

        history = RecruiterSearchHistory(**data)
        session.add(history)
        session.commit()
        session.refresh(history)

        return history

    finally:

        session.close()


def list_search_history_by_session(session_id):

    session = SessionLocal()

    try:

        statement = select(RecruiterSearchHistory).where(
            RecruiterSearchHistory.session_id == session_id
        ).order_by(
            RecruiterSearchHistory.created_at.desc()
        )

        return session.execute(statement).scalars().all()

    finally:

        session.close()


def list_search_history():

    session = SessionLocal()

    try:

        statement = select(RecruiterSearchHistory).order_by(
            RecruiterSearchHistory.created_at.desc()
        )

        return session.execute(statement).scalars().all()

    finally:

        session.close()


def get_search_history_by_id(history_id):

    session = SessionLocal()

    try:

        statement = select(RecruiterSearchHistory).where(
            RecruiterSearchHistory.id == history_id
        )

        return session.execute(statement).scalar_one_or_none()

    finally:

        session.close()


def delete_search_history(history_id) -> bool:

    session = SessionLocal()

    try:

        history = session.execute(
            select(RecruiterSearchHistory).where(
                RecruiterSearchHistory.id == history_id
            )
        ).scalar_one_or_none()

        if not history:
            return False

        session.delete(history)
        session.commit()

        return True

    finally:

        session.close()


def delete_search_history_by_session(session_id) -> int:

    session = SessionLocal()

    try:

        histories = session.execute(
            select(RecruiterSearchHistory).where(
                RecruiterSearchHistory.session_id == session_id
            )
        ).scalars().all()

        count = len(histories)
        for history in histories:
            session.delete(history)

        session.commit()

        return count

    finally:

        session.close()


def delete_all_search_history() -> int:

    session = SessionLocal()

    try:

        histories = session.execute(
            select(RecruiterSearchHistory)
        ).scalars().all()

        count = len(histories)
        for history in histories:
            session.delete(history)

        session.commit()

        return count

    finally:

        session.close()
