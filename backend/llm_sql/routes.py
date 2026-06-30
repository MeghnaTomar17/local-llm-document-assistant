import logging

from fastapi import APIRouter, HTTPException, status

from backend.llm_sql.schemas import RecruiterSearchRequest, RecruiterSearchResponse
from backend.llm_sql.services.recruiter_search_service import (
    RecruiterSearchService,
    SQLSearchValidationError,
)
from backend.llm_sql.services.sql_executor import SQLExecutionError
from backend.llm_sql.services.sql_generator import SQLGenerationError


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Recruiter Search"])


@router.post("/search", response_model=RecruiterSearchResponse)
def recruiter_search(payload: RecruiterSearchRequest) -> RecruiterSearchResponse:
    service = RecruiterSearchService()

    try:
        return service.search(payload.query)
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
