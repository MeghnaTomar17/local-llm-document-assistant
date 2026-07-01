import logging

from fastapi import APIRouter, HTTPException, status

from uuid import UUID

from backend.llm_sql.schemas import (
    RecruiterSearchHistoryItem,
    RecruiterSearchRequest,
    RecruiterSearchResponse,
)
from backend.llm_sql.services.recruiter_search_service import (
    RecruiterSearchService,
    SQLSearchValidationError,
)
from backend.llm_sql.services.sql_executor import SQLExecutionError
from backend.llm_sql.services.sql_generator import SQLGenerationError
from database.crud import (
    delete_all_search_history,
    delete_search_history,
    delete_search_history_by_session,
    get_search_history_by_id,
    list_search_history,
    list_search_history_by_session,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recruiter Search"])


@router.post("/search", response_model=RecruiterSearchResponse)
def recruiter_search(payload: RecruiterSearchRequest) -> RecruiterSearchResponse:
    service = RecruiterSearchService()

    try:
        return service.search(payload.query, session_id=payload.session_id)
    except SQLSearchValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Generated SQL failed validation.",
                "errors": exc.errors,
                "generated_sql": exc.generated_sql,
            },
        ) from exc
    except SQLGenerationError as exc:
        logger.exception("Recruiter SQL generation failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate SQL for recruiter search.",
        ) from exc
    except SQLExecutionError as exc:
        logger.exception("Recruiter SQL execution failed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute recruiter search.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected recruiter search failure.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Recruiter search failed.",
        ) from exc


@router.get("/search-history", response_model=list[RecruiterSearchHistoryItem])
def get_global_search_history() -> list[RecruiterSearchHistoryItem]:
    return list_search_history()


@router.delete("/search-history")
def remove_global_search_history():
    deleted = delete_all_search_history()
    return {"deleted": deleted}


@router.get("/search-history/item/{history_id}", response_model=RecruiterSearchHistoryItem)
def get_search_history_item(history_id: UUID):
    history = get_search_history_by_id(history_id)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search history item not found.",
        )
    return history


@router.get("/search-history/{session_id}", response_model=list[RecruiterSearchHistoryItem])
def get_search_history(session_id: UUID) -> list[RecruiterSearchHistoryItem]:
    return list_search_history_by_session(session_id)


@router.delete("/search-history/{history_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_search_history(history_id: UUID):
    if not delete_search_history(history_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search history item not found.",
        )
    return None


@router.delete("/search-history/session/{session_id}")
def remove_session_search_history(session_id: UUID):
    deleted = delete_search_history_by_session(session_id)
    return {"deleted": deleted}
