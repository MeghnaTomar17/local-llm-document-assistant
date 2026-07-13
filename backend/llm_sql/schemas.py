from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecruiterSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: UUID | None = None
    candidate_type: str | None = None


class RecruiterResumeResult(BaseModel):
    id: UUID | str | None = None
    candidate_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    skills: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    fresher: bool | None = None
    is_verified: bool | None = None
    processing_status: str | None = None
    extraction_status: str | None = None
    uploaded_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    notes: str | None = None
    hr_notes: str | None = None
    technical_notes: str | None = None
    final_notes: str | None = None
    hr_decision: str | None = None
    decision_at: datetime | str | None = None
    interview_marked: bool | None = None
    candidate_type: str | None = "EXTERNAL"
    search_score: float | None = None
    match_explanation: list[str] = Field(default_factory=list)
    match_details: dict[str, Any] = Field(default_factory=dict)
    normalized_candidate_skills: list[str] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    phone: str | None = None
    experience: str | None = None


class RecruiterSearchResponse(BaseModel):
    question: str
    generated_sql: str
    row_count: int
    execution_time_ms: float
    results: list[RecruiterResumeResult | dict[str, Any]]
    model_used: str | None = None
    requirement_analysis: dict[str, Any] = Field(default_factory=dict)
    debug_report_path: str | None = None
    relaxation_attempts: list[dict[str, Any]] = Field(default_factory=list)


class RecruiterSearchHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    session_id: UUID | None = None
    query: str
    generated_sql: str
    result_count: int
    results_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float | None = None
    model_used: str
    created_at: datetime
