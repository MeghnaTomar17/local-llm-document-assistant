from datetime import datetime
import logging
from pathlib import Path
import shutil
import uuid

from pdf_processor import (
    ALLOWED_EXTENSIONS,
    ask_llm,
    create_vector_store,
    export_chat,
    process_document,
)
from backend.services.metadata_service import ResumeMetadataService
from backend.services.resume_service import persist_resume_metadata


logger = logging.getLogger(__name__)
SESSION_METADATA_ROOT = Path("backend/session_metadata")


class ResumeSession:
    def __init__(self, session_id, vector_store):
        self.session_id = session_id
        self.documents = []
        self.vector_store = vector_store
        self.messages = []
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.updated_at = self.created_at

    @property
    def document(self):
        return self.documents[-1] if self.documents else None

    @property
    def display_name(self):
        return self.document["name"] if self.document else "Empty resume session"

    def add_document(self, document):
        self.documents.append(document)
        self.touch()

    def touch(self):
        self.updated_at = datetime.now().isoformat(timespec="seconds")


class DocumentService:
    def __init__(self):
        # Clean legacy per-session metadata folders. Metadata is now consolidated only.
        shutil.rmtree(SESSION_METADATA_ROOT, ignore_errors=True)
        self.sessions = {}
        self.active_session_id = None
        self.allowed_extensions = ALLOWED_EXTENSIONS
        self.metadata_service = ResumeMetadataService(output_dir=".")

    @property
    def active_session(self):
        if not self.active_session_id:
            return None
        return self.sessions.get(self.active_session_id)

    @property
    def documents(self):
        session = self.active_session
        return list(session.documents) if session else []

    @property
    def messages(self):
        session = self.active_session
        return session.messages if session else []

    def create_session(self):
        session_id = uuid.uuid4().hex
        session = ResumeSession(session_id, create_vector_store())
        self.sessions[session_id] = session
        self.active_session_id = session_id
        return session

    def add_document(self, file_path, display_name=None, session_id=None):
        result = self.add_documents([(file_path, display_name)])
        if not result["documents"]:
            detail = result["errors"][0]["error"] if result["errors"] else "Resume upload failed."
            raise RuntimeError(detail)
        return result["session"]

    def add_documents(self, file_items, session_id=None):
        added_documents = []
        errors = []
        sessions = []

        for file_path, display_name in file_items:
            session = self.create_session()
            try:
                document = self.process_resume_for_session(session, file_path, display_name)
                added_documents.append(document)
                sessions.append(session)
            except Exception as exc:
                self.sessions.pop(session.session_id, None)
                self.active_session_id = sessions[-1].session_id if sessions else None
                logger.exception("Failed to process resume %s: %s", display_name or file_path, exc)
                errors.append(
                    {
                        "file_name": display_name or Path(file_path).name,
                        "error": str(exc),
                    }
                )

        return {
            "session": sessions[-1] if sessions else None,
            "sessions": sessions,
            "documents": added_documents,
            "errors": errors,
        }

    def process_resume_for_session(self, session, file_path, display_name=None):
        document = process_document(
            file_path,
            vector_store=session.vector_store,
            reset_store=True,
            document_name=display_name,
        )
        metadata = self.metadata_service.add_resume(
            document["name"],
            document.get("text", ""),
        )
        resume = persist_resume_metadata(
            Path(file_path),
            document["name"],
            metadata,
        )
        document["metadata"] = metadata
        document["resume_id"] = str(resume.id)
        session.add_document(document)
        return document

    def reset(self):
        self.sessions = {}
        self.active_session_id = None
        shutil.rmtree(SESSION_METADATA_ROOT, ignore_errors=True)
        self.metadata_service.reset()
        return self.stats()

    def switch_session(self, session_id):
        if session_id not in self.sessions:
            raise ValueError("Resume session was not found.")
        self.active_session_id = session_id
        self.sessions[session_id].touch()
        return self.sessions[session_id]

    def ask(self, question, top_k=None, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        if not session:
            raise ValueError("Upload at least one resume before asking a question.")

        user_message = {
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "session_id": session.session_id,
        }
        session.messages.append(user_message)

        try:
            result = ask_llm(
                question,
                session.documents,
                session.messages,
                top_k=top_k,
                vector_store=session.vector_store,
            )
        except Exception:
            if session.messages and session.messages[-1] is user_message:
                session.messages.pop()
            session.touch()
            raise

        assistant_message = {
            "role": "assistant",
            "content": result["answer"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "retrieval": result["retrieval"],
            "prompt_size": result["prompt_size"],
            "session_id": session.session_id,
        }
        session.messages.append(assistant_message)
        session.touch()

        return {
            "answer": result["answer"],
            "retrieval": result["retrieval"],
            "prompt_size": len(result.get("answer", "")) if "prompt_size" not in result else result["prompt_size"],
            "message": assistant_message,
            "session_id": session.session_id,
        }

    def clear_chat(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        if session:
            session.messages = []
            session.touch()
        return session.messages if session else []

    def export_chat_text(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        return export_chat(session.messages if session else [])

    def stats(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        documents = session.documents if session else []
        messages = session.messages if session else []

        return {
            "active_session_id": session.session_id if session else None,
            "sessions": self.public_sessions(),
            "documents": [self.public_document(document) for document in documents],
            "document_count": len(documents),
            "total_pages": sum(document["page_count"] or 0 for document in documents),
            "total_characters": sum(document["character_count"] for document in documents),
            "total_chunks": sum(document["chunk_count"] for document in documents),
            "message_count": len(messages),
            "metadata_count": len(self.metadata_service.records),
        }

    def chat_history(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        return session.messages if session else []

    def public_sessions(self):
        return [
            {
                "session_id": session.session_id,
                "document": self.public_document(session.document) if session.document else None,
                "documents": [self.public_document(document) for document in session.documents],
                "display_name": session.display_name,
                "document_count": len(session.documents),
                "message_count": len(session.messages),
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "is_active": session.session_id == self.active_session_id,
            }
            for session in self.sessions.values()
        ]

    @staticmethod
    def public_document(document):
        return {
            "document_id": document["document_id"],
            "name": document["name"],
            "preview": document["preview"],
            "page_count": document["page_count"],
            "character_count": document["character_count"],
            "chunk_count": document["chunk_count"],
            "indexed_at": document["indexed_at"],
            "metadata": document.get("metadata", {}),
            "resume_id": document.get("resume_id"),
            "extraction_method": document.get("extraction_method"),
            "extraction_quality": document.get("extraction_quality", {}),
        }

    @staticmethod
    def public_chunk(chunk):
        return {
            "chunk_id": chunk.get("chunk_id"),
            "chunk_number": chunk.get("chunk_number"),
            "section": chunk.get("section"),
            "title": chunk.get("title"),
            "page": chunk.get("page"),
            "size": chunk.get("size"),
            "content": chunk.get("content", chunk.get("text", "")),
        }

    def debug_payload(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        if not session:
            return {
                "extracted_text": "",
                "chunks": [],
                "vector_chunks": [],
                "last_retrieval": None,
                "final_context": "",
                "metadata_records": self.metadata_service.records,
                "metadata_files": {
                    "txt": str(self.metadata_service.txt_path),
                    "csv": str(self.metadata_service.csv_path),
                },
            }

        last_retrieval = None
        for message in reversed(session.messages):
            if message.get("role") == "assistant" and message.get("retrieval"):
                last_retrieval = message["retrieval"]
                break

        return {
            "session_id": session.session_id,
            "document": self.public_document(session.document) if session.document else None,
            "documents": [self.public_document(document) for document in session.documents],
            "extracted_text": "\n\n".join(document.get("text", "") for document in session.documents),
            "extraction_method": session.document.get("extraction_method") if session.document else None,
            "extraction_quality": session.document.get("extraction_quality", {}) if session.document else {},
            "chunks": [
                self.public_chunk(chunk)
                for document in session.documents
                for chunk in document.get("chunks", [])
            ],
            "vector_chunks": [self.public_chunk(chunk) for chunk in session.vector_store.get("chunks", [])],
            "last_retrieval": last_retrieval,
            "retrieved_chunks": last_retrieval.get("chunks", []) if last_retrieval else [],
            "final_context": last_retrieval.get("context", "") if last_retrieval else "",
            "metadata_records": self.metadata_service.records,
            "metadata_files": {
                "txt": str(self.metadata_service.txt_path),
                "csv": str(self.metadata_service.csv_path),
            },
        }

    def metadata_payload(self, session_id=None):
        return {
            "records": self.metadata_service.records,
            "files": {
                "txt": str(self.metadata_service.txt_path),
                "csv": str(self.metadata_service.csv_path),
            },
        }


document_service = DocumentService()
