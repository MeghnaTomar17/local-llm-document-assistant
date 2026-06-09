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
        raise HTTPException(status_code=400, detail="Only PDF, DOC, and DOCX files are supported.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    file_path.write_bytes(await file.read())
    had_previous_document = bool(document_service.documents)

    try:
        document = document_service.add_document(file_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "document": document_service.public_document(document),
        "message": (
            "New document detected. Previous document context has been cleared."
            if had_previous_document
            else None
        ),
    }


@router.post("/ask")
async def ask_question(payload: dict):
    question = str(payload.get("question", "")).strip()
    top_k = int(payload.get("top_k", 4))

    if not question:
        raise HTTPException(status_code=400, detail="Question is required.")

    start = time.time()
    try:
        result = document_service.ask(question, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["response_time"] = time.time() - start
    result["message"]["response_time"] = result["response_time"]
    document_service.messages[-1]["response_time"] = result["response_time"]
    return result


@router.get("/stats")
def stats():
    return document_service.stats()


@router.get("/chat-history")
def chat_history():
    return {"messages": document_service.messages}


@router.post("/clear-chat")
def clear_chat():
    document_service.clear_chat()
    return {"messages": []}
