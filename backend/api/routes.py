from pathlib import Path
import time
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.document_service import document_service


router = APIRouter()
UPLOAD_DIR = Path("backend/uploads")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()
    if extension not in document_service.allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    file_path.write_bytes(await file.read())
    try:
        session = document_service.add_document(file_path, display_name=file.filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "session_id": session.session_id,
        "document": document_service.public_document(session.document),
        "sessions": document_service.public_sessions(),
        "message": "New resume session created. Previous resume sessions remain available.",
    }


@router.post("/ask")
async def ask_question(payload: dict):
    question = str(payload.get("question", "")).strip()
    top_k = int(payload["top_k"]) if payload.get("top_k") is not None else None
    session_id = payload.get("session_id")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    start = time.time()
    try:
        result = document_service.ask(question, top_k=top_k, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["response_time"] = time.time() - start
    result["message"]["response_time"] = result["response_time"]
    document_service.active_session.messages[-1]["response_time"] = result["response_time"]
    return result


@router.get("/stats")
def stats(session_id: str | None = None):
    return document_service.stats(session_id=session_id)


@router.get("/chat-history")
def chat_history(session_id: str | None = None):
    return {"messages": document_service.chat_history(session_id=session_id)}


@router.post("/clear-chat")
def clear_chat(payload: dict | None = None):
    session_id = payload.get("session_id") if payload else None
    return {"messages": document_service.clear_chat(session_id=session_id)}


@router.get("/sessions")
def sessions():
    return {
        "active_session_id": document_service.active_session_id,
        "sessions": document_service.public_sessions(),
    }


@router.get("/debug")
def debug(session_id: str | None = None):
    return document_service.debug_payload(session_id=session_id)


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
        "messages": session.messages,
        "stats": document_service.stats(),
    }
