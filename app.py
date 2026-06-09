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
    "Summary": "Provide a detailed summary of this document.",
    "Features": "List all key features and capabilities described.",
    "Architecture": "Explain the system architecture described in the document.",
    "Tech Stack": "List all technologies, frameworks, APIs, databases and tools mentioned.",
    "Use Cases": "List all use cases and applications mentioned.",
    "Future Scope": "List future enhancements and future scope discussed.",
}


st.set_page_config(
    page_title="Local LLM Document Assistant",
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
        st.caption("Page count is available for PDFs. Word documents do not expose reliable page counts until rendered.")


def ask_question(question):
    if not question.strip():
        return

    if not st.session_state.document:
        st.error("Upload a supported document before asking a question.")
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
    st.warning("⏳ Processing request. Please wait...")

st.sidebar.title("Quick Actions")
st.sidebar.caption("Run focused prompts on the uploaded document.")

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
        file_name="local-llm-chat-export.txt",
        mime="text/plain",
        use_container_width=True,
    )

st.markdown('<div class="app-title">Local LLM Document Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">Upload a document, inspect its stats, and ask questions using your local Ollama model.</div>',
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "Upload a document",
    type=["pdf", "doc", "docx"],
    accept_multiple_files=False,
    disabled=st.session_state.processing,
)

if uploaded_file:
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        st.error("Unsupported file type. Please upload only PDF, DOC, or DOCX files.")
    elif uploaded_file.name != st.session_state.uploaded_file_name:
        try:
            had_previous_document = st.session_state.document is not None
            saved_path = save_uploaded_file(uploaded_file)
            validate_file_type(saved_path)
            st.session_state.document = process_document(saved_path)
            st.session_state.uploaded_file_name = uploaded_file.name
            st.session_state.messages = []
            st.session_state.last_retrieval = None
            st.session_state.upload_notice = (
                "New document detected. Previous document context has been cleared."
                if had_previous_document
                else None
            )
            st.success(f"Loaded {uploaded_file.name}")
            st.rerun()
        except Exception as exc:
            st.session_state.document = None
            st.session_state.uploaded_file_name = None
            st.session_state.messages = []
            st.session_state.last_retrieval = None
            st.error(f"Could not process the uploaded file: {exc}")

if st.session_state.document:
    st.info(f"Current Document: {st.session_state.document['name']}")
    if st.session_state.upload_notice:
        st.success(st.session_state.upload_notice)
    display_stats(st.session_state.document)
    with st.expander("Document Preview", expanded=False):
        st.text_area(
            "Extracted text preview",
            value=st.session_state.document["preview"],
            height=260,
            disabled=True,
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
                    f"{chunk['document_name']} #{chunk['chunk_number']}"
                    for chunk in retrieval["chunks"]
                ]
                st.caption(
                    f"Sources: {', '.join(chunk_numbers)} | "
                    f"Chunks used: {retrieval['chunk_count']} | "
                    f"Context size: {retrieval['context_size']:,} characters | "
                    f"Prompt size: {message.get('prompt_size', 0):,} characters"
                )
                with st.expander("Retrieval Diagnostics", expanded=False):
                    for chunk in retrieval["chunks"]:
                        similarity = chunk.get("similarity")
                        score = f"{similarity:.3f}" if similarity is not None else "N/A"
                        st.markdown(
                            f"**{chunk['document_name']} - Chunk {chunk['chunk_number']}**  \n"
                            f"Section: {chunk['section']}  \n"
                            f"Size: {chunk['size']:,} characters  \n"
                            f"Similarity: {score}"
                        )
                        st.text(chunk["text"][:900])

question = st.chat_input(
    "Ask a question about the uploaded document",
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
