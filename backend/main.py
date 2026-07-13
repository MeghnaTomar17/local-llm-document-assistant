import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.llm_sql.routes import router as recruiter_search_router
from backend.llm_sql.services.recruiter_search_service import warm_recruiter_search_service
from backend.routes.resume_routes import router as resume_router


def configure_console_logging() -> None:
    """Ensure backend service logs are visible in the server terminal."""

    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    for handler in root_logger.handlers:
        handler.setLevel(level)
        if handler.formatter is None:
            handler.setFormatter(formatter)

    for logger_name in ("backend", "database", "pdf_processor"):
        logging.getLogger(logger_name).setLevel(level)


configure_console_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Resume Intelligence Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Accept-Ranges"],
)

app.include_router(router)
app.include_router(resume_router)
app.include_router(recruiter_search_router)


@app.on_event("startup")
def startup_recruiter_search() -> None:
    warm_recruiter_search_service()
    logger.info("Backend startup complete. Recruiter search service is ready.")


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Resume Intelligence Assistant"}
