from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from backend.schemas.resume import ResumeListResponse, ResumeResponse, ResumeUpdate
from backend.services.resume_service import (
    IntegrityError,
    SQLAlchemyError,
    delete_resume_response,
    get_resume_response,
    list_resume_response,
    update_resume_response,
)


router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.get("", response_model=ResumeListResponse)
def get_resumes() -> ResumeListResponse:
    try:
        return list_resume_response()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch resumes.",
        ) from exc


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(resume_id: UUID):
    try:
        resume = get_resume_response(resume_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch resume.",
        ) from exc

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
def update_resume(resume_id: UUID, payload: ResumeUpdate):
    try:
        resume = update_resume_response(resume_id, payload)
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume update conflicts with existing data.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update resume.",
        ) from exc

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return resume


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: UUID) -> Response:
    try:
        deleted = delete_resume_response(resume_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete resume.",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
