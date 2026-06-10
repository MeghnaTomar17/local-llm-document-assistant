from datetime import datetime
import uuid

from pdf_processor import (
    ALLOWED_EXTENSIONS,
    ask_llm,
    create_vector_store,
    export_chat,
    process_document,
)


class ResumeSession:
    def __init__(self, session_id, document, vector_store):
        self.session_id = session_id
        self.document = document
        self.vector_store = vector_store
        self.messages = []
        self.created_at = datetime.now().isoformat(timespec="seconds")
        self.updated_at = self.created_at

    def touch(self):
        self.updated_at = datetime.now().isoformat(timespec="seconds")


class DocumentService:
    def __init__(self):
        self.sessions = {}
        self.active_session_id = None
        self.allowed_extensions = ALLOWED_EXTENSIONS

    @property
    def active_session(self):
        if not self.active_session_id:
            return None
        return self.sessions.get(self.active_session_id)

    @property
    def documents(self):
        session = self.active_session
        return [session.document] if session else []

    @property
    def messages(self):
        session = self.active_session
        return session.messages if session else []

    def add_document(self, file_path, display_name=None):
        vector_store = create_vector_store()
        document = process_document(
            file_path,
            vector_store=vector_store,
            reset_store=True,
            document_name=display_name,
        )
        session_id = uuid.uuid4().hex
        session = ResumeSession(session_id, document, vector_store)
        self.sessions[session_id] = session
        self.active_session_id = session_id
        return session

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

        result = ask_llm(
            question,
            session.document,
            session.messages,
            top_k=top_k,
            vector_store=session.vector_store,
        )
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
            "prompt_size": result["prompt_size"],
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
        documents = [session.document] if session else []
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
        }

    def chat_history(self, session_id=None):
        session = self.switch_session(session_id) if session_id else self.active_session
        return session.messages if session else []

    def public_sessions(self):
        return [
            {
                "session_id": session.session_id,
                "document": self.public_document(session.document),
                "display_name": session.document["name"],
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
            }

        last_retrieval = None
        for message in reversed(session.messages):
            if message.get("role") == "assistant" and message.get("retrieval"):
                last_retrieval = message["retrieval"]
                break

        return {
            "session_id": session.session_id,
            "document": self.public_document(session.document),
            "extracted_text": session.document.get("text", ""),
            "chunks": [self.public_chunk(chunk) for chunk in session.document.get("chunks", [])],
            "vector_chunks": [self.public_chunk(chunk) for chunk in session.vector_store.get("chunks", [])],
            "last_retrieval": last_retrieval,
            "retrieved_chunks": last_retrieval.get("chunks", []) if last_retrieval else [],
            "final_context": last_retrieval.get("context", "") if last_retrieval else "",
        }


document_service = DocumentService()
