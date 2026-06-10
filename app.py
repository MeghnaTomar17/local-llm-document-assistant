from pathlib import Path
from datetime import datetime
import time
import uuid

import streamlit as st

from pdf_processor import (
    ALLOWED_EXTENSIONS,
    ask_llm,
    export_chat,
    process_document,
    validate_file_type,
)


UPLOAD_DIR = Path("uploads")

QUICK_ACTIONS = {
    "Resume Summary": "Summarize the resume.",
    "Contact Information": "Show contact information from the resume.",
    "Skills": "Show skills from the resume.",
    "Technical Skills": "Show technical skills from the resume.",
    "Education": "Show education from the resume.",
    "Experience": "Show experience from the resume.",
    "Projects": "Show projects from the resume.",
    "Certifications": "Show certifications from the resume.",
    "Achievements": "Show achievements from the resume.",
    "Languages": "Show languages from the resume.",
    "Career Highlights": "List the career highlights from the resume.",
    "Recruiter Summary": "Write a concise recruiter summary using only the resume.",
}


st.set_page_config(
    page_title="Resume Intelligence Assistant",
    layout="wide",
)

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 2rem;
            max-width: 1180px;
        }

        .app-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }

        .app-subtitle {
            color: #64748b;
            margin-bottom: 1.25rem;
        }

        .stat-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 1rem 0 1.25rem;
        }

        .stat-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.9rem 1rem;
            background: #ffffff;
        }

        .stat-label {
            color: #64748b;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0;
            margin-bottom: 0.25rem;
        }

        .stat-value {
            color: #0f172a;
            font-size: 1.3rem;
            font-weight: 700;
        }

        @media (max-width: 720px) {
            .stat-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_state():
    defaults = {
        "document": None,
        "uploaded_file_name": None,
        "messages": [],
        "pending_question": None,
        "processing": False,
        "last_retrieval": None,
        "upload_notice": None,
        "debug_mode": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def save_uploaded_file(uploaded_file):
    UPLOAD_DIR.mkdir(exist_ok=True)
    extension = Path(uploaded_file.name).suffix.lower()
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    file_path.write_bytes(uploaded_file.getbuffer())
    return file_path


def display_stats(document):
    page_count = document["page_count"] if document["page_count"] is not None else "N/A"

    st.markdown(
        f"""
        <div class="stat-row">
            <div class="stat-card">
                <div class="stat-label">Number of pages</div>
                <div class="stat-value">{page_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Character count</div>
                <div class="stat-value">{document["character_count"]:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Chunk count</div>
                <div class="stat-value">{document["chunk_count"]:,}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if document["page_count"] is None:
        st.caption("Page count is available for PDFs. DOCX resumes do not expose reliable page counts until rendered.")


def ask_question(question):
    if not question.strip():
        return

    if not st.session_state.document:
        st.error("Upload a supported resume before asking a question.")
        return

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    st.session_state.processing = True

    with st.spinner("Generating response..."):
        start_time = time.time()
        try:
            result = ask_llm(question, st.session_state.document, st.session_state.messages)
            elapsed_time = time.time() - start_time
            st.session_state.last_retrieval = result["retrieval"]
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "time": elapsed_time,
                    "retrieval": result["retrieval"],
                    "prompt_size": result["prompt_size"],
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
        except Exception as exc:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"Could not generate a response: {exc}",
                    "time": None,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
        finally:
            st.session_state.processing = False


initialize_state()

if st.session_state.processing:
    st.warning("Processing request. Please wait...")

st.sidebar.title("Quick Actions")
st.sidebar.caption("Run focused prompts on the uploaded resume.")

for label, prompt in QUICK_ACTIONS.items():
    if st.sidebar.button(label, use_container_width=True, disabled=(st.session_state.document is None or st.session_state.processing)):
        st.session_state.pending_question = prompt
        st.rerun()

if st.sidebar.button("Clear Chat", use_container_width=True, disabled=st.session_state.processing):
    st.session_state.messages = []
    st.session_state.last_retrieval = None

if st.session_state.messages:
    st.sidebar.download_button(
        "Export Chat TXT",
        data=export_chat(st.session_state.messages),
        file_name="resume-intelligence-chat-export.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.session_state.debug_mode = st.sidebar.checkbox(
    "Developer debug mode",
    value=st.session_state.debug_mode,
)

st.markdown('<div class="app-title">Resume Intelligence Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Upload a resume, inspect its stats, and ask questions using your local Ollama model.</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a resume",
    type=["pdf", "docx"],
    accept_multiple_files=False,
    disabled=st.session_state.processing,
)

if uploaded_file:
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        st.error("Unsupported file type. Please upload only PDF or DOCX resumes.")
    elif uploaded_file.name != st.session_state.uploaded_file_name:
        try:
            had_previous_resume = st.session_state.document is not None
            saved_path = save_uploaded_file(uploaded_file)
            validate_file_type(saved_path)
            st.session_state.document = process_document(saved_path, document_name=uploaded_file.name)
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.messages = []
            st.session_state.last_retrieval = None
            st.session_state.upload_notice = (
                "New resume detected. Previous resume context has been cleared."
                if had_previous_resume
                else None
            )
            st.success(f"Loaded {uploaded_file.name}")
            st.rerun()
        except Exception as exc:
            st.session_state.document = None
            st.session_state.uploaded_file_name = None
            st.session_state.messages = []
            st.session_state.last_retrieval = None
            st.error(f"Could not process the uploaded resume: {exc}")

if st.session_state.document:
    st.info(f"Current Resume: {st.session_state.document['name']}")
    if st.session_state.upload_notice:
        st.success(st.session_state.upload_notice)
    display_stats(st.session_state.document)
    with st.expander("Resume Preview", expanded=False):
        st.text_area(
            "Extracted text preview",
            value=st.session_state.document["preview"],
            height=260,
            disabled=True,
            label_visibility="collapsed",
        )

    if st.session_state.debug_mode:
        with st.expander("Developer Debug", expanded=False):
            st.subheader("Extracted Text")
            st.text_area(
                "Extracted resume text",
                value=st.session_state.document.get("text", ""),
                height=220,
                label_visibility="collapsed",
            )

            st.subheader("Generated Chunks")
            st.json(
                [
                    {
                        "chunk_id": chunk.get("chunk_id"),
                        "chunk_number": chunk.get("chunk_number"),
                        "section": chunk.get("section"),
                        "title": chunk.get("title"),
                        "page": chunk.get("page"),
                        "size": chunk.get("size"),
                        "content": chunk.get("content"),
                    }
                    for chunk in st.session_state.document.get("chunks", [])
                ]
            )

            st.subheader("Retrieved Chunks")
            st.json(st.session_state.last_retrieval.get("chunks", []) if st.session_state.last_retrieval else [])

            st.subheader("Final Context Sent to LLM")
            st.text_area(
                "Final context",
                value=st.session_state.last_retrieval.get("context", "") if st.session_state.last_retrieval else "",
                height=220,
                label_visibility="collapsed",
            )

st.divider()

st.subheader("Chat")

if not st.session_state.messages:
    st.info("Ask a free-form question or use a quick action from the sidebar.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant" and message.get("time") is not None:
            st.caption(f"Response generated in {message['time']:.2f} seconds")
            retrieval = message.get("retrieval")
            if retrieval:
                chunk_numbers = [
                    f"{chunk['section']} | Chunk {chunk['chunk_number']} | Page {chunk.get('page') or 'N/A'}"
                    for chunk in retrieval["chunks"]
                ]
                st.caption(
                    f"Retrieved: {', '.join(chunk_numbers)} | "
                    f"Chunks used: {retrieval['chunk_count']} | "
                    f"Context size: {retrieval['context_size']:,} characters | "
                    f"Prompt size: {message.get('prompt_size', 0):,} characters | "
                    f"Strategy: {retrieval.get('strategy', 'semantic')}"
                )
                with st.expander("Retrieval Diagnostics", expanded=False):
                    for chunk in retrieval["chunks"]:
                        similarity = chunk.get("similarity")
                        score = f"{similarity:.3f}" if similarity is not None else "N/A"
                        st.markdown(
                            f"**{chunk['document_name']} - Chunk {chunk['chunk_number']}**  \n"
                            f"Section: {chunk['section']}  \n"
                            f"Title: {chunk.get('title') or chunk['section']}  \n"
                            f"Page: {chunk.get('page') or 'N/A'}  \n"
                            f"Size: {chunk['size']:,} characters  \n"
                            f"Similarity: {score}"
                        )
                        st.text(chunk.get("content", chunk["text"])[:900])

question = st.chat_input(
    "Ask a question about the uploaded resume",
    disabled=st.session_state.processing,
)

if question:
    st.session_state.pending_question = question
    st.rerun()

if (
    st.session_state.pending_question
    and not st.session_state.processing
):
    pending = st.session_state.pending_question
    st.session_state.pending_question = None

    ask_question(pending)

    st.rerun()
