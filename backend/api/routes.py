from pathlib import Path
import time
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.services.document_service import document_service
from backend.services.resume_service import DuplicateCandidateError


router = APIRouter()
UPLOAD_DIR = Path("backend/uploads")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024


async def save_upload_to_disk(file: UploadFile, file_path: Path) -> None:
    total_bytes = 0
    with file_path.open("wb") as destination:
        while True:
            chunk = await file.read(UPLOAD_CHUNK_SIZE)
            if not chunk:
                break

            total_bytes += len(chunk)
            if total_bytes > MAX_UPLOAD_BYTES:
                destination.close()
                file_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail="Resume file is too large. Maximum allowed size is 25 MB.",
                )

            destination.write(chunk)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in document_service.allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    await save_upload_to_disk(file, file_path)
    try:
        session = document_service.add_document(file_path, display_name=file.filename)
    except DuplicateCandidateError as exc:
        return exc.payload
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "session_id": session.session_id,
        "document": document_service.public_document(session.document),
        "documents": [document_service.public_document(document) for document in session.documents],
        "sessions": document_service.public_sessions(),
        "metadata": document_service.metadata_payload(),
        "message": "Resume uploaded to the active session.",
    }


@router.post("/upload-batch")
async def upload_documents(
    files: list[UploadFile] = File(...),
    session_id: str | None = Form(None),
):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_items = []
    errors = []

    for file in files:
        extension = Path(file.filename or "").suffix.lower()
        if extension not in document_service.allowed_extensions:
            errors.append(
                {
                    "file_name": file.filename or "",
                    "error": "Only PDF and DOCX resumes are supported.",
                }
            )
            continue

        file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
        try:
            await save_upload_to_disk(file, file_path)
            file_items.append((file_path, file.filename))
        except HTTPException as exc:
            errors.append(
                {
                    "file_name": file.filename or "",
                    "error": str(exc.detail),
                }
            )
        except Exception as exc:
            errors.append(
                {
                    "file_name": file.filename or "",
                    "error": str(exc),
                }
            )

    try:
        result = document_service.add_documents(file_items, session_id=session_id) if file_items else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    session = result["session"] if result else document_service.active_session
    processing_errors = result["errors"] if result else []
    errors.extend(processing_errors)
    duplicate = next((error for error in errors if error.get("duplicate")), None)

    return {
        **(duplicate or {}),
        "session_id": session.session_id if session else None,
        "documents": [document_service.public_document(document) for document in (session.documents if session else [])],
        "uploaded_documents": [
            document_service.public_document(document)
            for document in (result["documents"] if result else [])
        ],
        "errors": errors,
        "sessions": document_service.public_sessions(),
        "metadata": document_service.metadata_payload(session.session_id if session else None),
        "message": f"Processed {len(result['documents']) if result else 0} resume(s); {len(errors)} failed.",
    }


@router.post("/ask")
async def ask_question(payload: dict):
    question = str(payload.get("question", "")).strip()
    top_k = int(payload["top_k"]) if payload.get("top_k") is not None else None
    session_id = payload.get("session_id")
    resume_id = payload.get("resume_id")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    start = time.time()
    try:
        result = document_service.ask(
            question,
            top_k=top_k,
            session_id=session_id,
            resume_id=resume_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["response_time"] = time.time() - start
    result["message"]["response_time"] = result["response_time"]
    document_service.set_last_response_time(
        result["session_id"],
        result["message"],
        result["response_time"],
    )
    return result


@router.get("/stats")
def stats(session_id: str | None = None, resume_id: str | None = None):
    return document_service.stats(session_id=session_id, resume_id=resume_id)


@router.get("/chat-history")
def chat_history(session_id: str | None = None, resume_id: str | None = None):
    return {
        "messages": document_service.chat_history(
            session_id=session_id,
            resume_id=resume_id,
        )
    }


@router.post("/clear-chat")
def clear_chat(payload: dict | None = None):
    session_id = payload.get("session_id") if payload else None
    resume_id = payload.get("resume_id") if payload else None
    return {
        "messages": document_service.clear_chat(
            session_id=session_id,
            resume_id=resume_id,
        )
    }


@router.get("/sessions")
def sessions():
    sessions_payload = document_service.public_sessions()
    active_session = next(
        (session for session in sessions_payload if session.get("is_active")),
        None,
    )
    return {
        "active_session_id": (
            document_service.active_session_id
            or (active_session.get("session_id") if active_session else None)
        ),
        "sessions": sessions_payload,
    }


@router.post("/sessions")
def create_session(payload: dict | None = None):
    title = str((payload or {}).get("title", "Resume Session")).strip() or "Resume Session"
    session = document_service.create_session(title=title)
    return {
        "active_session_id": session.session_id,
        "session": {
            "session_id": session.session_id,
            "id": session.session_id,
            "title": title,
            "display_name": title,
            "documents": [],
            "document": None,
            "document_count": 0,
            "message_count": 0,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "is_active": True,
        },
        "sessions": document_service.public_sessions(),
    }


@router.get("/sessions/{session_id}/resumes")
def session_resumes(session_id: str):
    try:
        return {
            "session_id": session_id,
            "resumes": document_service.session_resumes(session_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/debug")
def debug(session_id: str | None = None):
    return document_service.debug_payload(session_id=session_id)


@router.get("/metadata")
def metadata(session_id: str | None = None):
    return document_service.metadata_payload(session_id=session_id)


@router.post("/reset")
def reset_runtime_state():
    return document_service.reset()


@router.post("/switch-session")
def switch_session(payload: dict):
    session_id = str(payload.get("session_id", "")).strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required.")

    try:
        session = document_service.switch_session(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {
        "active_session_id": session.session_id,
        "document": document_service.public_document(session.document),
        "documents": [document_service.public_document(document) for document in session.documents],
        "messages": session.messages,
        "stats": document_service.stats(),
    }
