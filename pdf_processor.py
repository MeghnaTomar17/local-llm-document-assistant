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


ALLOWED_EXTENSIONS = {".pdf", ".docx"}
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 160
MAX_LOGICAL_CHUNK_CHARS = 2200
DEFAULT_TOP_K = 2
MAX_MEMORY_MESSAGES = 3
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

RESUME_SECTIONS = {
    "Contact Information": {
        "contact",
        "contact information",
        "personal information",
        "personal details",
    },
    "Summary": {
        "summary",
        "professional summary",
        "career summary",
        "profile",
        "objective",
        "career objective",
        "about me",
    },
    "Education": {
        "education",
        "academic background",
        "academics",
        "qualification",
        "qualifications",
        "educational qualification",
    },
    "Skills": {
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "competencies",
        "technologies",
        "technical proficiencies",
    },
    "Experience": {
        "experience",
        "work experience",
        "professional experience",
        "employment",
        "employment history",
        "internship",
        "internships",
    },
    "Projects": {
        "projects",
        "project",
        "academic projects",
        "personal projects",
        "professional projects",
        "selected projects",
    },
    "Certifications": {
        "certifications",
        "certification",
        "certificates",
        "courses",
        "training",
    },
    "Achievements": {
        "achievements",
        "awards",
        "honors",
        "honours",
        "accomplishments",
    },
    "Languages": {
        "languages",
        "language",
        "known languages",
    },
}

SUMMARY_QUERY_TERMS = {
    "summarize",
    "summary",
    "overview",
    "profile",
    "recruiter summary",
    "career highlights",
    "highlight",
    "highlights",
}

SUMMARY_SECTION_PRIORITY = [
    "Summary",
    "Experience",
    "Projects",
    "Skills",
    "Education",
    "Certifications",
    "Achievements",
]


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


def create_vector_store():
    return {
        "index": None,
        "chunks": [],
        "ids": set(),
    }


def reset_vector_store(vector_store=None):
    global _faiss_index, _vector_chunks, _vector_ids
    if vector_store is None:
        _faiss_index = None
        _vector_chunks = []
        _vector_ids = set()
    else:
        vector_store["index"] = None
        vector_store["chunks"] = []
        vector_store["ids"] = set()


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
        "text": "\n\n".join(paragraphs),
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
    chunk_number = 1
    sections = split_resume_sections(text)

    for section in sections:
        if section["section"] == "Projects":
            logical_parts = split_project_section(section)
        else:
            logical_parts = split_large_section_by_paragraph(section)

        for part in logical_parts:
            content = part["content"].strip()
            if not content:
                continue

            chunk_id = f"{document_id}-{chunk_number}"
            chunks.append(
                build_chunk(
                    chunk_id=chunk_id,
                    chunk_number=chunk_number,
                    document_id=document_id,
                    document_name=document_name,
                    section=part["section"],
                    title=part["title"],
                    page=part["page"],
                    content=content,
                )
            )
            chunk_number += 1

    return chunks


def build_chunk(chunk_id, chunk_number, document_id, document_name, section, title, page, content):
    return {
        "chunk_id": chunk_id,
        "chunk_number": chunk_number,
        "section": section,
        "title": title or section,
        "page": page,
        "content": content,
        "text": content,
        "document_id": document_id,
        "document_name": document_name,
        "size": len(content),
    }


def split_resume_sections(text):
    sections = []
    current_section = "Contact Information"
    current_title = "Contact Information"
    current_page = None
    lines = []
    seen_heading = False

    def flush():
        content = "\n".join(line for line, _ in lines).strip()
        if not content:
            return

        page = first_page(lines) or current_page
        sections.append(
            {
                "section": current_section,
                "title": current_title,
                "page": page,
                "lines": list(lines),
                "content": content,
            }
        )

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        page_match = re.match(r"^\[Page\s+(\d+)\]$", line.strip(), flags=re.IGNORECASE)
        if page_match:
            current_page = int(page_match.group(1))
            continue

        detected_section = detect_resume_section(line)
        if detected_section:
            flush()
            lines = []
            current_section = detected_section
            current_title = detected_section
            seen_heading = True
            remainder = section_heading_remainder(line, detected_section)
            if remainder:
                lines.append((remainder, current_page))
            continue

        if line.strip() or seen_heading or current_section == "Contact Information":
            lines.append((line, current_page))

    flush()

    if sections:
        return sections

    return [
        {
            "section": "Summary",
            "title": "Summary",
            "page": None,
            "lines": [(text, None)],
            "content": text.strip(),
        }
    ]


def detect_resume_section(line):
    clean = normalize_heading(line)
    if not clean or len(clean) > 80:
        return None

    for section, aliases in RESUME_SECTIONS.items():
        section_aliases = aliases | {section.lower()}
        if clean in section_aliases:
            return section
        for alias in section_aliases:
            if re.match(rf"^\s*{re.escape(alias)}\s*[:|-]", line, flags=re.IGNORECASE):
                return section
    return None


def section_heading_remainder(line, section):
    clean_line = line.strip()
    if ":" not in clean_line:
        return ""

    heading, remainder = clean_line.split(":", 1)
    if detect_resume_section(heading) == section:
        return remainder.strip()
    return ""


def normalize_heading(line):
    clean = re.sub(r"\s+", " ", line).strip().lower()
    clean = clean.strip(":-|")
    clean = re.sub(r"^[#*\-\u2022\s]+", "", clean)
    clean = re.sub(r"[^a-z\s/&]", "", clean)
    clean = clean.replace("&", " and ")
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def split_large_section_by_paragraph(section):
    content = section["content"].strip()
    if len(content) <= MAX_LOGICAL_CHUNK_CHARS:
        return [section]

    paragraphs = paragraphs_from_lines(section["lines"])
    if not paragraphs:
        return [section]

    chunks = []
    current_lines = []

    for paragraph in paragraphs:
        paragraph_text = lines_to_text(paragraph)
        current_text = lines_to_text(current_lines)
        would_exceed = len(current_text) + len(paragraph_text) + 2 > MAX_LOGICAL_CHUNK_CHARS

        if current_lines and would_exceed:
            chunks.append(section_part(section, current_lines, section["title"]))
            current_lines = []

        current_lines.extend(paragraph)

    if current_lines:
        chunks.append(section_part(section, current_lines, section["title"]))

    return chunks


def split_project_section(section):
    project_blocks = split_project_blocks(section["lines"])
    if not project_blocks:
        return split_large_section_by_paragraph(section)

    chunks = []
    for block in project_blocks:
        title = infer_project_title(block) or "Project"
        block_text = lines_to_text(block)

        if len(block_text) <= MAX_LOGICAL_CHUNK_CHARS:
            chunks.append(section_part(section, block, title))
            continue

        for paragraph in paragraphs_from_lines(block):
            paragraph_text = lines_to_text(paragraph)
            if paragraph_text:
                chunks.append(section_part(section, paragraph, title))

    return chunks


def split_project_blocks(lines):
    blocks = []
    current = []
    previous_blank = True

    for index, item in enumerate(lines):
        line = item[0].strip()
        if not line:
            if current:
                current.append(item)
            previous_blank = True
            continue

        starts_new_project = current and is_project_title_line(line) and (
            previous_blank or is_distinct_project_name(line)
        )
        if starts_new_project:
            blocks.append(trim_blank_lines(current))
            current = [item]
        else:
            current.append(item)
        previous_blank = False

    if current:
        blocks.append(trim_blank_lines(current))

    if len(blocks) == 1:
        paragraphs = paragraphs_from_lines(lines)
        title_like_count = sum(1 for paragraph in paragraphs if paragraph and is_project_title_line(paragraph[0][0].strip()))
        if title_like_count > 1:
            return paragraphs

    return [block for block in blocks if lines_to_text(block)]


def is_project_title_line(line):
    clean = strip_list_marker(line).strip()
    if not clean:
        return False
    if re.match(
        r"^(tech stack|technologies|tools|role|duration|description|github|link|live|demo|features|responsibilities|impact)\s*:",
        clean,
        flags=re.IGNORECASE,
    ):
        return False
    if detect_resume_section(clean):
        return False
    if len(clean) > 120:
        return False
    if clean.endswith("."):
        return False
    if re.search(r"https?://|@|\b\d{10}\b", clean, flags=re.IGNORECASE):
        return False
    return len(clean.split()) <= 14


def infer_project_title(lines):
    for line, _ in lines:
        clean = strip_list_marker(line).strip(" :-|")
        if clean:
            return clean[:120]
    text = lines_to_text(lines)
    return text[:80] if text else None


def is_distinct_project_name(line):
    clean = strip_list_marker(line).strip(" :-|")
    if not clean or len(clean.split()) > 3:
        return False
    return bool(re.search(r"[a-z][A-Z]", clean)) or bool(re.match(r"^[A-Z][A-Za-z0-9_-]{3,}$", clean))


def paragraphs_from_lines(lines):
    paragraphs = []
    current = []

    for item in lines:
        line = item[0]
        if line.strip():
            current.append(item)
        elif current:
            paragraphs.append(current)
            current = []

    if current:
        paragraphs.append(current)

    return paragraphs


def section_part(section, lines, title):
    return {
        "section": section["section"],
        "title": title,
        "page": first_page(lines) or section.get("page"),
        "content": lines_to_text(lines),
        "lines": lines,
    }


def first_page(lines):
    for _, page in lines:
        if page is not None:
            return page
    return None


def lines_to_text(lines):
    return "\n".join(line for line, _ in lines).strip()


def trim_blank_lines(lines):
    trimmed = list(lines)
    while trimmed and not trimmed[0][0].strip():
        trimmed.pop(0)
    while trimmed and not trimmed[-1][0].strip():
        trimmed.pop()
    return trimmed


def is_bullet_line(line):
    return bool(re.match(r"^(\*|-|\u2022|\d+[\).\s])\s*", line.strip()))


def strip_list_marker(line):
    return re.sub(r"^(\*|-|\u2022|\d+[\).\s])\s*", "", line.strip())


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


def get_faiss_index(embedding_dimension, vector_store=None):
    global _faiss_index
    if vector_store is not None:
        if vector_store.get("index") is None:
            faiss = get_faiss()
            vector_store["index"] = faiss.IndexFlatIP(embedding_dimension)
        return vector_store["index"]

    if _faiss_index is None:
        faiss = get_faiss()
        _faiss_index = faiss.IndexFlatIP(embedding_dimension)
    return _faiss_index


def build_vector_index(document, vector_store=None):
    global _vector_chunks

    chunks = document["chunks"]
    if not chunks:
        return

    model = get_embedding_model()
    texts = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(texts, normalize_embeddings=True)
    embeddings = np.asarray(embeddings, dtype="float32")
    index = get_faiss_index(embeddings.shape[1], vector_store=vector_store)

    new_embeddings = []
    new_chunks = []
    vector_ids = vector_store["ids"] if vector_store is not None else _vector_ids

    for chunk, embedding in zip(chunks, embeddings):
        vector_id = f"{document['document_id']}-{chunk['chunk_number']}"
        if vector_id in vector_ids:
            continue

        vector_ids.add(vector_id)
        new_embeddings.append(embedding)
        new_chunks.append(
            {
                "chunk_id": chunk["chunk_id"],
                "text": chunk["text"],
                "content": chunk["content"],
                "document_id": chunk["document_id"],
                "document_name": chunk["document_name"],
                "chunk_number": chunk["chunk_number"],
                "section": chunk["section"],
                "title": chunk["title"],
                "page": chunk["page"],
                "size": chunk["size"],
            }
        )

    if new_embeddings:
        index.add(np.asarray(new_embeddings, dtype="float32"))
        if vector_store is None:
            _vector_chunks.extend(new_chunks)
        else:
            vector_store["chunks"].extend(new_chunks)


def process_document(file_path, vector_store=None, reset_store=True, document_name=None):
    if reset_store:
        reset_vector_store(vector_store)

    path = Path(file_path)
    extraction = extract_text(path)
    text = extraction["text"]
    document_id = uuid.uuid4().hex
    display_name = document_name or path.name
    chunks = create_chunks(text, document_id=document_id, document_name=display_name)

    document = {
        "document_id": document_id,
        "name": display_name,
        "text": text,
        "preview": text[:2500],
        "chunks": chunks,
        "page_count": extraction["page_count"],
        "character_count": len(text),
        "chunk_count": len(chunks),
        "indexed_at": datetime.now().isoformat(timespec="seconds"),
    }
    build_vector_index(document, vector_store=vector_store)
    return document


def retrieve_relevant_chunks(question, document_or_documents, top_k=None, vector_store=None):
    documents = _as_document_list(document_or_documents)
    document_ids = [document["document_id"] for document in documents]
    if not document_ids:
        return {"chunks": [], "context": "", "context_size": 0, "chunk_count": 0}

    vector_chunks = vector_store["chunks"] if vector_store is not None else _vector_chunks
    candidate_chunks = [
        chunk
        for chunk in vector_chunks
        if chunk.get("document_id") in document_ids
    ]

    direct_retrieval = retrieve_by_resume_intent(question, candidate_chunks)
    if direct_retrieval is not None:
        return build_retrieval_payload(
            direct_retrieval["chunks"],
            strategy=direct_retrieval["strategy"],
            query_type=direct_retrieval["query_type"],
        )

    model = get_embedding_model()
    query_embedding = model.encode([question], normalize_embeddings=True)
    query_embedding = np.asarray(query_embedding, dtype="float32")
    index = get_faiss_index(query_embedding.shape[1], vector_store=vector_store)

    if index.ntotal == 0:
        return {"chunks": [], "context": "", "context_size": 0, "chunk_count": 0}

    search_count = index.ntotal
    scores, indexes = index.search(query_embedding, search_count)

    retrieved = []
    semantic_top_k = top_k or DEFAULT_TOP_K
    for score, chunk_index in zip(scores[0], indexes[0]):
        if chunk_index < 0 or chunk_index >= len(vector_chunks):
            continue

        metadata = vector_chunks[chunk_index]
        if metadata["document_id"] not in document_ids:
            continue

        retrieved.append(
            {
                "text": metadata["text"],
                "content": metadata.get("content", metadata["text"]),
                "chunk_id": metadata.get("chunk_id"),
                "document_id": metadata.get("document_id"),
                "document_name": metadata.get("document_name"),
                "chunk_number": metadata.get("chunk_number"),
                "section": metadata.get("section"),
                "title": metadata.get("title"),
                "page": metadata.get("page"),
                "size": metadata.get("size", len(metadata["text"])),
                "distance": float(1.0 - score),
                "similarity": float(score),
            }
        )
        if len(retrieved) >= semantic_top_k:
            break

    return build_retrieval_payload(retrieved, strategy="semantic", query_type="general")


def retrieve_by_resume_intent(question, chunks):
    if not chunks:
        return None

    project_chunks = [chunk for chunk in chunks if chunk.get("section") == "Projects"]
    project_chunk = find_project_chunk(question, project_chunks)
    if project_chunk:
        return {
            "chunks": [project_chunk],
            "strategy": "project",
            "query_type": "specific_project",
        }

    if is_summary_query(question):
        selected_chunks = select_summary_chunks(chunks)
        if selected_chunks:
            return {
                "chunks": selected_chunks,
                "strategy": "summary",
                "query_type": "summary",
            }

    requested_section = detect_requested_section(question)
    if requested_section:
        section_chunks = [
            chunk
            for chunk in chunks
            if chunk.get("section") == requested_section
        ]
        if section_chunks:
            if requested_section == "Projects":
                selected_chunks = section_chunks
            else:
                selected_chunks = section_chunks[:1]
            return {
                "chunks": selected_chunks,
                "strategy": "section",
                "query_type": "section",
            }

    return None


def find_project_chunk(question, project_chunks):
    question_normalized = normalize_for_match(question)
    if not question_normalized:
        return None

    for chunk in project_chunks:
        title = chunk.get("title") or ""
        title_normalized = normalize_for_match(title)
        if title_normalized and title_normalized in question_normalized:
            return chunk

    subject = extract_project_subject(question)
    if subject:
        subject_normalized = normalize_for_match(subject)
        for chunk in project_chunks:
            title_normalized = normalize_for_match(chunk.get("title") or "")
            if subject_normalized and subject_normalized in title_normalized:
                return chunk

    return None


def extract_project_subject(question):
    match = re.search(
        r"\b(?:about|explain|describe|details of|detail of|tell me about)\s+([a-zA-Z0-9][a-zA-Z0-9 ._-]{1,80})",
        question,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return re.sub(r"[?.!,]+$", "", match.group(1)).strip()


def detect_requested_section(question):
    question_normalized = normalize_for_match(question)
    if not question_normalized:
        return None

    for section, aliases in RESUME_SECTIONS.items():
        for alias in aliases | {section.lower()}:
            alias_normalized = normalize_for_match(alias)
            if re.search(rf"\b{re.escape(alias_normalized)}\b", question_normalized):
                return section
    return None


def is_summary_query(question):
    question_normalized = normalize_for_match(question)
    return any(term in question_normalized for term in SUMMARY_QUERY_TERMS)


def select_summary_chunks(chunks):
    selected = []
    for section in SUMMARY_SECTION_PRIORITY:
        section_chunk = next((chunk for chunk in chunks if chunk.get("section") == section), None)
        if section_chunk:
            selected.append(section_chunk)
        if len(selected) >= 5:
            break
    return selected or chunks[:4]


def build_retrieval_payload(retrieved, strategy, query_type):
    context = "\n\n".join(
        (
            f"[{chunk['document_name']} | Chunk {chunk['chunk_number']} | "
            f"{chunk['section']} | {chunk.get('title') or chunk['section']} | Page {chunk.get('page') or 'N/A'}]\n"
            f"{chunk['content']}"
        )
        for chunk in retrieved
    )

    return {
        "chunks": retrieved,
        "context": context,
        "context_size": len(context),
        "chunk_count": len(retrieved),
        "strategy": strategy,
        "query_type": query_type,
    }


def normalize_for_match(value):
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", str(value).lower())
    return re.sub(r"\s+", " ", clean).strip()


def build_prompt(question, retrieval, chat_history=None):
    memory = format_recent_history(chat_history or [])
    memory_block = f"\nRECENT CONVERSATION:\n{memory}\n" if memory else ""

    return f"""
You are a Resume Intelligence Assistant.

Use ONLY the resume context and recent conversation shown here.
Never invent employers, dates, skills, projects, certifications, achievements, education, or contact details.
Never mix details from different projects.
Never combine unrelated resume sections into one answer unless the user asks for a summary or overview.
If information is unavailable in the resume context, clearly say that the resume does not provide that information.
Use recent conversation only to resolve follow-up references, not to add facts outside the resume.
Mention the section name and chunk number you relied on when useful.
{memory_block}
RESUME CONTEXT:
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


def ask_llm(question, document_or_documents, chat_history=None, top_k=None, vector_store=None):
    retrieval = retrieve_relevant_chunks(
        question,
        document_or_documents,
        top_k=top_k,
        vector_store=vector_store,
    )
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
    lines = ["Resume Intelligence Assistant - Chat Export", ""]

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
