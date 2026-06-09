from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

import numpy as np
import requests
from docx import Document
from pypdf import PdfReader


ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 160
DEFAULT_TOP_K = 2
MAX_MEMORY_MESSAGES = 3
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


@dataclass
class RagChunk:
    chunk_number: int
    text: str
    section: str
    document_id: str
    document_name: str

    @property
    def size(self):
        return len(self.text)


_embedding_model = None
_faiss = None
_faiss_index = None
_vector_chunks = []
_vector_ids = set()


def reset_vector_store():
    global _faiss_index, _vector_chunks, _vector_ids
    _faiss_index = None
    _vector_chunks = []
    _vector_ids = set()


def validate_file_type(file_path):
    extension = Path(file_path).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise ValueError(f"Unsupported file type '{extension}'. Allowed file types: {allowed}.")
    return extension


def extract_text(file_path):
    extension = validate_file_type(file_path)

    if extension == ".pdf":
        return _extract_pdf_text(file_path)

    if extension == ".docx":
        return _extract_docx_text(file_path)

    return _extract_doc_text(file_path)


def _extract_pdf_text(file_path):
    reader = PdfReader(file_path)
    pages = []

    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if page_text:
            pages.append(f"\n[Page {index}]\n{page_text.strip()}")

    return {
        "text": "\n".join(pages).strip(),
        "page_count": len(reader.pages),
    }


def _extract_docx_text(file_path):
    document = Document(file_path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    return {
        "text": "\n".join(paragraphs),
        "page_count": None,
    }


def _extract_doc_text(file_path):
    converted_path = _convert_doc_to_docx(file_path)
    try:
        result = _extract_docx_text(converted_path)
        result["page_count"] = None
        return result
    finally:
        try:
            Path(converted_path).unlink(missing_ok=True)
        except OSError:
            pass


def _convert_doc_to_docx(file_path):
    source_path = Path(file_path)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        command = [
            "soffice",
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(temp_dir_path),
            str(source_path),
        ]

        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Legacy DOC files require LibreOffice to be installed and available as 'soffice'. "
                "Please upload a PDF or DOCX file, or install LibreOffice to process DOC files."
            ) from exc

        converted_path = temp_dir_path / f"{source_path.stem}.docx"
        if completed.returncode != 0 or not converted_path.exists():
            raise RuntimeError(
                "Could not convert the DOC file to DOCX. "
                f"LibreOffice output: {completed.stderr or completed.stdout}"
            )

        persistent_path = Path(tempfile.gettempdir()) / converted_path.name
        persistent_path.write_bytes(converted_path.read_bytes())
        return persistent_path


def create_chunks(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP, document_id=None, document_name="Document"):
    if not text:
        return []

    document_id = document_id or uuid.uuid4().hex
    chunks = []
    start = 0
    chunk_number = 1

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end].strip()

        if chunk_text:
            chunks.append(
                {
                    "chunk_number": chunk_number,
                    "text": chunk_text,
                    "section": infer_section_title(chunk_text),
                    "document_id": document_id,
                    "document_name": document_name,
                    "size": len(chunk_text),
                }
            )
            chunk_number += 1

        if end == len(text):
            break
        start = max(0, end - overlap)

    return chunks


def infer_section_title(chunk_text):
    for line in chunk_text.splitlines():
        clean = re.sub(r"\s+", " ", line).strip(" :-")
        if not clean:
            continue
        if clean.startswith("[Page"):
            return clean[:80]
        if len(clean) <= 90:
            return clean
        return clean[:87] + "..."
    return "Untitled section"


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for semantic retrieval. "
                "Install dependencies with 'pip install -r requirements.txt'."
            ) from exc
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_faiss():
    global _faiss
    if _faiss is None:
        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError(
                "faiss-cpu is required for vector search. "
                "Install dependencies with 'pip install -r requirements.txt'."
            ) from exc
        _faiss = faiss
    return _faiss


def get_faiss_index(embedding_dimension):
    global _faiss_index
    if _faiss_index is None:
        faiss = get_faiss()
        _faiss_index = faiss.IndexFlatIP(embedding_dimension)
    return _faiss_index


def build_vector_index(document):
    global _vector_chunks

    chunks = document["chunks"]
    if not chunks:
        return

    model = get_embedding_model()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")
    index = get_faiss_index(embeddings.shape[1])

    new_embeddings = []
    new_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        vector_id = f"{document['document_id']}-{chunk['chunk_number']}"
        if vector_id in _vector_ids:
            continue

        _vector_ids.add(vector_id)
        new_embeddings.append(embedding)
        new_chunks.append(
            {
                "text": chunk["text"],
                "document_id": chunk["document_id"],
                "document_name": chunk["document_name"],
                "chunk_number": chunk["chunk_number"],
                "section": chunk["section"],
                "size": chunk["size"],
            }
        )

    if new_embeddings:
        index.add(np.asarray(new_embeddings, dtype="float32"))
        _vector_chunks.extend(new_chunks)


def process_document(file_path):
    reset_vector_store()

    path = Path(file_path)
    extraction = extract_text(path)
    text = extraction["text"]
    document_id = uuid.uuid4().hex
    chunks = create_chunks(text, document_id=document_id, document_name=path.name)

    document = {
        "document_id": document_id,
        "name": path.name,
        "text": text,
        "preview": text[:2500],
        "chunks": chunks,
        "page_count": extraction["page_count"],
        "character_count": len(text),
        "chunk_count": len(chunks),
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
    }
    build_vector_index(document)
    return document


def retrieve_relevant_chunks(question, document_or_documents, top_k=DEFAULT_TOP_K):
    documents = _as_document_list(document_or_documents)
    document_ids = [document["document_id"] for document in documents]
    if not document_ids:
        return {"chunks": [], "context": "", "context_size": 0, "chunk_count": 0}

    model = get_embedding_model()
    query_embedding = model.encode([question], normalize_embeddings=True)
    query_embedding = np.asarray(query_embedding, dtype="float32")
    index = get_faiss_index(query_embedding.shape[1])

    if index.ntotal == 0:
        return {"chunks": [], "context": "", "context_size": 0, "chunk_count": 0}

    search_count = index.ntotal
    scores, indexes = index.search(query_embedding, search_count)

    retrieved = []
    for score, chunk_index in zip(scores[0], indexes[0]):
        if chunk_index < 0 or chunk_index >= len(_vector_chunks):
            continue

        metadata = _vector_chunks[chunk_index]
        if metadata["document_id"] not in document_ids:
            continue

        retrieved.append(
            {
                "text": metadata["text"],
                "document_id": metadata.get("document_id"),
                "document_name": metadata.get("document_name"),
                "chunk_number": metadata.get("chunk_number"),
                "section": metadata.get("section"),
                "size": metadata.get("size", len(metadata["text"])),
                "distance": float(1.0 - score),
                "similarity": float(score),
            }
        )
        if len(retrieved) >= top_k:
            break

    context = "\n\n".join(
        f"[{chunk['document_name']} | Chunk {chunk['chunk_number']} | {chunk['section']}]\n{chunk['text']}"
        for chunk in retrieved
    )

    return {
        "chunks": retrieved,
        "context": context,
        "context_size": len(context),
        "chunk_count": len(retrieved),
    }


def build_prompt(question, retrieval, chat_history=None):
    memory = format_recent_history(chat_history or [])
    memory_block = f"\nRECENT CONVERSATION:\n{memory}\n" if memory else ""

    return f"""
You are a document assistant.

Answer using only the document context and recent conversation shown here.
Use the recent conversation to resolve follow-up questions and references to earlier answers.
If the answer is not present in the context, say that the document does not provide enough information.
Mention the chunk numbers you relied on when useful.
{memory_block}
DOCUMENT CONTEXT:
{retrieval["context"]}

QUESTION:
{question}
""".strip()


def format_recent_history(messages, limit=MAX_MEMORY_MESSAGES):
    recent = messages[-limit:]
    formatted = []

    for message in recent:
        role = message.get("role", "user").title()
        content = str(message.get("content", "")).strip()
        if content:
            formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


def ask_llm(question, document_or_documents, chat_history=None, top_k=DEFAULT_TOP_K):
    retrieval = retrieve_relevant_chunks(question, document_or_documents, top_k=top_k)
    prompt = build_prompt(question, retrieval, chat_history)
    print("\n" + "="*50)
    print("Prompt Size:", len(prompt))
    print("Retrieved Chunks:", retrieval["chunk_count"])
    print("Context Size:", retrieval["context_size"])
    print("="*50)
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        },
        timeout=300,
    )
    response.raise_for_status()

    return {
        "answer": response.json()["response"],
        "retrieval": retrieval,
        "prompt_size": len(prompt),
    }


def export_chat(messages):
    lines = ["Local LLM Document Assistant - Chat Export", ""]

    for message in messages:
        timestamp = message.get("timestamp") or datetime.now().isoformat(timespec="seconds")
        role = message.get("role", "message").upper()
        lines.append(f"[{timestamp}] {role}")
        lines.append(str(message.get("content", "")))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _as_document_list(document_or_documents):
    if document_or_documents is None:
        return []
    if isinstance(document_or_documents, dict):
        return [document_or_documents]
    return list(document_or_documents)
