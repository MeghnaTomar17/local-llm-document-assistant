from datetime import datetime
import logging
from pathlib import Path
import shutil
import uuid
import hashlib
from threading import RLock

from pdf_processor import (
    ALLOWED_EXTENSIONS,
    ask_llm,
    build_vector_index,
    create_vector_store,
    export_chat,
    process_document,
)
from backend.services.metadata_service import ResumeMetadataService
from backend.services.resume_service import DuplicateCandidateError, persist_resume_metadata
from backend.services.session_service import (
    activate_persistent_session,
    create_persistent_session,
    ensure_resume_workspace,
    ensure_session,
    public_resumes_for_session,
    public_sessions as public_persistent_sessions,
)
from database.crud import (
    get_resume_by_hash,
    get_resume_by_id,
    get_resume_chunks,
    list_resumes_by_session,
    save_resume_chunks,
    update_session_chat_history,
)


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
        self._lock = RLock()
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

    def create_session(self, title="Resume Session"):
        with self._lock:
            persistent_session = create_persistent_session(title=title)
            session_id = str(persistent_session.id)
            session = ResumeSession(session_id, create_vector_store())
            session.created_at = persistent_session.created_at.isoformat()
            session.updated_at = persistent_session.updated_at.isoformat()
            self.sessions[session_id] = session
            self.active_session_id = session_id
            return session

    def add_document(self, file_path, display_name=None, session_id=None):
        with self._lock:
            result = self.add_documents([(file_path, display_name)], session_id=session_id)
            if not result["documents"]:
                if result["errors"] and result["errors"][0].get("duplicate"):
                    duplicate_error = DuplicateCandidateError.__new__(DuplicateCandidateError)
                    duplicate_error.payload = result["errors"][0]
                    ValueError.__init__(duplicate_error, duplicate_error.payload["message"])
                    raise duplicate_error
                detail = result["errors"][0]["error"] if result["errors"] else "Resume upload failed."
                raise RuntimeError(detail)
            return result["session"]

    def add_documents(self, file_items, session_id=None):
        with self._lock:
            added_documents = []
            errors = []
            sessions = []

            if not session_id:
                for file_path, display_name in file_items:
                    try:
                        session, document = self.process_resume_workspace(
                            file_path,
                            display_name,
                        )
                        sessions.append(session)
                        if document:
                            added_documents.append(document)
                    except DuplicateCandidateError as exc:
                        errors.append(exc.payload)
                    except Exception as exc:
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

            default_title = (
                str(file_items[0][1] or Path(file_items[0][0]).name)
                if len(file_items) == 1
                else "Resume Session"
            )
            persistent_session = ensure_session(session_id, title=default_title)
            session_key = str(persistent_session.id)
            session = self.sessions.get(session_key)

            if not session:
                session = ResumeSession(session_key, create_vector_store())
                session.created_at = persistent_session.created_at.isoformat()
                session.updated_at = persistent_session.updated_at.isoformat()
                self.sessions[session_key] = session

            self.active_session_id = session_key
            sessions.append(session)

            for index, (file_path, display_name) in enumerate(file_items):
                try:
                    existing = get_resume_by_hash(self.resume_hash(file_path))
                    if existing:
                        raise DuplicateCandidateError(existing)

                    document = self.process_resume_for_session(
                        session,
                        file_path,
                        display_name,
                        reset_store=(index == 0 and not session.documents),
                    )
                    added_documents.append(document)
                except DuplicateCandidateError as exc:
                    errors.append(exc.payload)
                except Exception as exc:
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

    def process_resume_workspace(self, file_path, display_name=None):
        existing = get_resume_by_hash(self.resume_hash(file_path))

        if existing:
            raise DuplicateCandidateError(existing)

        session = ResumeSession("pending", create_vector_store())
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
            session_id=None,
        )

        session.session_id = str(resume.session_id)
        document["metadata"] = metadata
        document["resume_id"] = str(resume.id)
        save_resume_chunks(resume.id, document.get("chunks", []))
        session.add_document(document)

        self.sessions[session.session_id] = session
        self.active_session_id = session.session_id

        return session, document

    @staticmethod
    def resume_hash(file_path):
        return hashlib.sha256(Path(file_path).read_bytes()).hexdigest()

    def process_resume_for_session(self, session, file_path, display_name=None, reset_store=True):
        document = process_document(
            file_path,
            vector_store=session.vector_store,
            reset_store=reset_store,
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
            session_id=uuid.UUID(str(session.session_id)),
        )
        document["metadata"] = metadata
        document["resume_id"] = str(resume.id)
        save_resume_chunks(resume.id, document.get("chunks", []))
        session.add_document(document)
        return document

    def reset(self):
        with self._lock:
            self.sessions = {}
            self.active_session_id = None
            shutil.rmtree(SESSION_METADATA_ROOT, ignore_errors=True)
            self.metadata_service.reset()
            return self.stats()

    def switch_session(self, session_id):
        with self._lock:
            persistent_session = activate_persistent_session(session_id)
            session_key = str(persistent_session.id)

            if session_key not in self.sessions:
                self.sessions[session_key] = self.load_session_from_database(persistent_session)

            self.active_session_id = session_key
            self.sessions[session_key].touch()
            return self.sessions[session_key]

    def switch_resume_session(self, resume_id):
        with self._lock:
            resume = get_resume_by_id(resume_id)
            if not resume:
                raise ValueError("Resume was not found.")

            persistent_session = ensure_resume_workspace(resume, active=True)
            if not persistent_session:
                raise ValueError("Resume session was not found.")

            session_key = str(persistent_session.id)
            self.sessions[session_key] = self.load_resume_session_from_database(
                persistent_session,
                resume,
            )
            self.active_session_id = session_key
            self.sessions[session_key].touch()

            return self.sessions[session_key]

    def load_session_from_database(self, persistent_session):
        session = ResumeSession(str(persistent_session.id), create_vector_store())
        session.created_at = persistent_session.created_at.isoformat()
        session.updated_at = persistent_session.updated_at.isoformat()
        session.messages = list(persistent_session.chat_history or [])

        resumes = list_resumes_by_session(persistent_session.id)
        for index, resume in enumerate(reversed(resumes)):
            document = self.build_document_from_resume(
                resume,
                vector_store=session.vector_store,
                reset_store=(index == 0),
            )
            if not document:
                continue
            session.add_document(document)

        return session

    def load_resume_session_from_database(self, persistent_session, resume):
        session = ResumeSession(str(persistent_session.id), create_vector_store())
        session.created_at = persistent_session.created_at.isoformat()
        session.updated_at = persistent_session.updated_at.isoformat()
        session.messages = list(persistent_session.chat_history or [])

        document = self.build_document_from_resume(
            resume,
            vector_store=session.vector_store,
            reset_store=True,
        )
        if document:
            session.add_document(document)

        return session

    def build_document_from_resume(self, resume, vector_store, reset_store=True):
        stored_document = self.build_document_from_stored_chunks(
            resume,
            vector_store=vector_store,
            reset_store=reset_store,
        )
        if stored_document:
            return stored_document

        path = Path(resume.file_path)
        if not path.exists():
            logger.warning("Stored resume file is missing: %s", path)
            return None

        try:
            document = process_document(
                path,
                vector_store=vector_store,
                reset_store=reset_store,
                document_name=resume.original_file_name,
            )
        except Exception as exc:
            logger.exception("Failed to rebuild session document %s: %s", resume.id, exc)
            return None

        document["metadata"] = {
            "Resume File Name": resume.original_file_name,
            "Candidate Name": resume.candidate_name or "",
            "Email": resume.email or "",
            "Phone Number": resume.phone_number or "",
            "Cities": resume.cities or [],
            "Skills": resume.skills or [],
            "Fresher": "Yes" if resume.fresher else "No",
        }
        document["resume_id"] = str(resume.id)
        save_resume_chunks(resume.id, document.get("chunks", []))
        return document

    def build_document_from_stored_chunks(self, resume, vector_store, reset_store=True):
        stored_chunks = get_resume_chunks(resume.id)
        if not stored_chunks:
            return None

        if reset_store:
            from pdf_processor import reset_vector_store

            reset_vector_store(vector_store)

        document_id = str(resume.id)
        chunks = [
            {
                "chunk_id": f"{document_id}-{chunk.chunk_index}",
                "chunk_number": chunk.chunk_index,
                "section": chunk.section or "Resume",
                "title": chunk.title or chunk.section or "Resume",
                "page": chunk.page_number,
                "content": chunk.content,
                "text": chunk.content,
                "document_id": document_id,
                "document_name": resume.original_file_name,
                "size": len(chunk.content),
            }
            for chunk in stored_chunks
        ]
        text = "\n\n".join(chunk["content"] for chunk in chunks)
        document = {
            "document_id": document_id,
            "name": resume.original_file_name,
            "text": text,
            "preview": text[:2500],
            "chunks": chunks,
            "page_count": None,
            "character_count": len(text),
            "chunk_count": len(chunks),
            "indexed_at": datetime.now().isoformat(timespec="seconds"),
            "extraction_method": "stored_chunks",
            "extraction_quality": {},
            "metadata": {
                "Resume File Name": resume.original_file_name,
                "Candidate Name": resume.candidate_name or "",
                "Email": resume.email or "",
                "Phone Number": resume.phone_number or "",
                "Cities": resume.cities or [],
                "Skills": resume.skills or [],
                "Fresher": "Yes" if resume.fresher else "No",
            },
            "resume_id": str(resume.id),
        }
        build_vector_index(document, vector_store=vector_store)
        return document

    def ask(self, question, top_k=None, session_id=None, resume_id=None):
        with self._lock:
            if resume_id:
                session = self.switch_resume_session(resume_id)
            else:
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
            update_session_chat_history(session.session_id, session.messages)

            return {
                "answer": result["answer"],
                "retrieval": result["retrieval"],
                "prompt_size": len(result.get("answer", "")) if "prompt_size" not in result else result["prompt_size"],
                "message": assistant_message,
                "session_id": session.session_id,
            }

    def set_last_response_time(self, session_id, message, response_time):
        with self._lock:
            session = self.sessions.get(str(session_id))
            if not session:
                return

            message["response_time"] = response_time
            for stored_message in reversed(session.messages):
                if (
                    stored_message.get("role") == "assistant"
                    and stored_message.get("timestamp") == message.get("timestamp")
                    and stored_message.get("session_id") == message.get("session_id")
                ):
                    stored_message["response_time"] = response_time
                    update_session_chat_history(session.session_id, session.messages)
                    return

    def clear_chat(self, session_id=None, resume_id=None):
        with self._lock:
            if resume_id:
                session = self.switch_resume_session(resume_id)
            else:
                session = self.switch_session(session_id) if session_id else self.active_session
            if session:
                session.messages = []
                session.touch()
                update_session_chat_history(session.session_id, session.messages)
            return session.messages if session else []

    def export_chat_text(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        return export_chat(session.messages if session else [])

    def stats(self, session_id=None, resume_id=None):
        with self._lock:
            if resume_id:
                session = self.switch_resume_session(resume_id)
            else:
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

    def chat_history(self, session_id=None, resume_id=None):
        with self._lock:
            if resume_id:
                session = self.switch_resume_session(resume_id)
            else:
                session = self.switch_session(session_id) if session_id else self.active_session
            return session.messages if session else []

    def public_sessions(self):
        return public_persistent_sessions()

    def session_resumes(self, session_id):
        return public_resumes_for_session(session_id)

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
