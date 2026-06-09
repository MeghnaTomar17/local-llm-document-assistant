from datetime import datetime

from pdf_processor import ALLOWED_EXTENSIONS, ask_llm, export_chat, process_document


class DocumentService:
    def __init__(self):
        self.documents = []
        self.messages = []
        self.allowed_extensions = ALLOWED_EXTENSIONS

    def add_document(self, file_path):
        self.documents = []
        self.messages = []
        document = process_document(file_path)
        self.documents = [document]
        return document

    def ask(self, question, top_k=4):
        if not self.documents:
            raise ValueError("Upload at least one document before asking a question.")

        user_message = {
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        self.messages.append(user_message)

        result = ask_llm(question, self.documents, self.messages, top_k=top_k)
        assistant_message = {
            "role": "assistant",
            "content": result["answer"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "retrieval": result["retrieval"],
            "prompt_size": result["prompt_size"],
        }
        self.messages.append(assistant_message)

        return {
            "answer": result["answer"],
            "retrieval": result["retrieval"],
            "prompt_size": result["prompt_size"],
            "message": assistant_message,
        }

    def clear_chat(self):
        self.messages = []

    def export_chat_text(self):
        return export_chat(self.messages)

    def stats(self):
        return {
            "documents": [self.public_document(document) for document in self.documents],
            "document_count": len(self.documents),
            "total_pages": sum(document["page_count"] or 0 for document in self.documents),
            "total_characters": sum(document["character_count"] for document in self.documents),
            "total_chunks": sum(document["chunk_count"] for document in self.documents),
            "message_count": len(self.messages),
        }

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


document_service = DocumentService()
