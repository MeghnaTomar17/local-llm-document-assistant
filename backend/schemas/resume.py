from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


HRDecision = Literal["PENDING", "ON_HOLD", "ACCEPTED", "REJECTED"]


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID | None = None
    original_file_name: str
    stored_file_name: str | None = None
    file_path: str | None = None
    mime_type: str | None = None
    candidate_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    skills: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    fresher: bool
    processing_status: str
    is_verified: bool
    extraction_status: str
    notes: str | None = None
    hr_notes: str | None = None
    technical_notes: str | None = None
    final_notes: str | None = None
    hr_decision: HRDecision = "PENDING"
    decision_at: datetime | None = None
    uploaded_at: datetime
    updated_at: datetime


class ResumeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    skills: list[str] | None = None
    cities: list[str] | None = None
    fresher: bool | None = None
    hr_notes: str | None = None
    technical_notes: str | None = None
    final_notes: str | None = None
    hr_decision: HRDecision | None = None


class ResumeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID | None = None
    original_file_name: str
    candidate_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    skills: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    fresher: bool
    processing_status: str
    is_verified: bool
    extraction_status: str
    notes: str | None = None
    hr_notes: str | None = None
    technical_notes: str | None = None
    final_notes: str | None = None
    hr_decision: HRDecision = "PENDING"
    decision_at: datetime | None = None
    uploaded_at: datetime
    updated_at: datetime


class ResumeListResponse(BaseModel):
    total: int
    resumes: list[ResumeListItem]


class ResumeChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_id: UUID
    chunk_index: int
    section: str | None = None
    title: str | None = None
    page_number: int | None = None
    content: str
    created_at: datetime
