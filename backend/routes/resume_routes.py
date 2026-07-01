from uuid import UUID
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse

from backend.schemas.resume import ResumeChunkResponse, ResumeListResponse, ResumeResponse, ResumeUpdate
from backend.services.resume_service import (
    IntegrityError,
    SQLAlchemyError,
    delete_resume_response,
    get_resume_download,
    get_resume_chunks_response,
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


@router.get("/{resume_id}/download")
def download_resume(resume_id: UUID) -> StreamingResponse:
    try:
        download = get_resume_download(resume_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download resume.",
        ) from exc

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    original_file_name, mime_type, resume_blob = download

    if not resume_blob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file content was not found in the database.",
        )

    safe_file_name = quote(original_file_name or "resume", safe="")
    headers = {
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{safe_file_name}"
        )
    }

    return StreamingResponse(
        BytesIO(resume_blob),
        media_type=mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/{resume_id}/preview")
def preview_resume(resume_id: UUID) -> StreamingResponse:
    try:
        download = get_resume_download(resume_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview resume.",
        ) from exc

    if not download:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )

    original_file_name, mime_type, resume_blob = download

    if not resume_blob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume file content was not found in the database.",
        )

    safe_file_name = quote(original_file_name or "resume", safe="")
    headers = {
        "Content-Disposition": (
            f"inline; filename*=UTF-8''{safe_file_name}"
        )
    }

    return StreamingResponse(
        BytesIO(resume_blob),
        media_type=mime_type or "application/octet-stream",
        headers=headers,
    )


@router.get("/{resume_id}/chunks", response_model=list[ResumeChunkResponse])
def get_resume_chunks(resume_id: UUID):
    try:
        resume = get_resume_response(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )
        return get_resume_chunks_response(resume_id)
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch resume chunks.",
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
