import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    LargeBinary,
    String,
    Text,
    func,
)

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB, UUID

from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class Resume(Base):

    __tablename__ = "resumes"

    # -------------------------
    # Primary Key
    # -------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # -------------------------
    # Resume Information
    # -------------------------
    resume_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )

    # -------------------------
    # Resume File Information
    # -------------------------

    original_file_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    stored_file_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    file_path: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mime_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    resume_blob: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True,
        deferred=True,
    )

    # -------------------------
    # Candidate Metadata
    # -------------------------
    candidate_name: Mapped[str | None] = mapped_column(Text)

    email: Mapped[str | None] = mapped_column(Text)

    phone_number: Mapped[str | None] = mapped_column(Text)

    skills: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
    )

    cities: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
    )

    fresher: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    # -------------------------
    # Processing Status
    # -------------------------

    processing_status: Mapped[str] = mapped_column(
        String(20),
        default="UPLOADED",
    )
    # -------------------------
    # Recruiter Fields
    # -------------------------
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    extraction_status: Mapped[str] = mapped_column(
        String(20),
        default="SUCCESS",
    )

    notes: Mapped[str | None] = mapped_column(Text)

    # -------------------------
    # Timestamps
    # -------------------------
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
