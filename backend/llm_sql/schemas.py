from typing import Any

from pydantic import BaseModel, Field


class RecruiterSearchRequest(BaseModel):
    query: str = Field(min_length=1)


class RecruiterSearchResponse(BaseModel):
    question: str
    generated_sql: str
    row_count: int
    execution_time_ms: float
    results: list[dict[str, Any]]
