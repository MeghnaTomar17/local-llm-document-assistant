import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    Text,
    Integer,
    UniqueConstraint,
    func,
)

from datetime import datetime

from sqlalchemy.dialects.postgresql import JSONB, UUID

from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class RecruiterSession(Base):

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Resume Session",
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    last_accessed: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    chat_history: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="session",
    )

    search_history: Mapped[list["RecruiterSearchHistory"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class RecruiterSearchHistory(Base):

    __tablename__ = "recruiter_search_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=True,
        index=True,
    )

    query: Mapped[str] = mapped_column(Text, nullable=False)

    generated_sql: Mapped[str] = mapped_column(Text, nullable=False)

    result_count: Mapped[int] = mapped_column(default=0, nullable=False)

    results_snapshot: Mapped[list] = mapped_column(
        JSONB,
        default=list,
    )

    execution_time_ms: Mapped[float | None] = mapped_column(nullable=True)

    model_used: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    session: Mapped[RecruiterSession] = relationship(
        back_populates="search_history",
    )


class ResumeChunk(Base):

    __tablename__ = "resume_chunks"
    __table_args__ = (
        UniqueConstraint("resume_id", "chunk_index", name="uq_resume_chunks_resume_id_chunk_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    section: Mapped[str | None] = mapped_column(Text)

    title: Mapped[str | None] = mapped_column(Text)

    page_number: Mapped[int | None] = mapped_column(Integer)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    resume: Mapped["Resume"] = relationship(
        back_populates="chunks",
    )


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

    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id"),
        nullable=True,
        index=True,
    )

    session: Mapped[RecruiterSession | None] = relationship(
        back_populates="resumes",
    )

    chunks: Mapped[list[ResumeChunk]] = relationship(
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeChunk.chunk_index",
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

    hr_decision: Mapped[str] = mapped_column(
        String(20),
        default="PENDING",
        nullable=False,
    )

    decision_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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
