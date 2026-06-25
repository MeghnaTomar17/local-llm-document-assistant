from datetime import datetime, timezone

from database.connection import SessionLocal
from database.models import Resume
from sqlalchemy import select


EDITABLE_RESUME_FIELDS = {
    "candidate_name",
    "email",
    "phone_number",
    "skills",
    "cities",
    "fresher",
    "notes",
}


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

            for key, value in data.items():

                if hasattr(existing, key):
                    setattr(existing, key, value)

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

def list_resumes():

    session = SessionLocal()

    try:

        statement = select(Resume)

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
                setattr(resume, key, value)

        resume.is_verified = True
        resume.updated_at = datetime.now(timezone.utc)

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
