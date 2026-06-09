# Local LLM Document Assistant

A local document intelligence assistant powered by Ollama, Llama 3.2, semantic RAG, FastAPI, and React.

The project still supports the Streamlit app, PDF/DOC/DOCX upload, chunking, question answering, quick actions, chat, document statistics, and response timing. It now adds conversational memory, source attribution, document preview, chat export, retrieval diagnostics, and FAISS-backed semantic search.

## What Changed

### Phase 1: Advanced Document Intelligence

* Recent chat history is included in prompts for follow-up questions.
* Assistant responses include source chunks, chunk count, context size, prompt size, sections, and similarity diagnostics.
* Uploaded document text preview is available in an expandable panel.
* Chat can be exported as TXT with timestamps and user/assistant messages.

### Phase 2: Real RAG

* Retrieval now uses `sentence-transformers` embeddings.
* Chunk vectors are stored in an in-process FAISS index.
* Similarity search retrieves the top relevant chunks before calling Ollama.
* The assistant is intentionally single-document: uploading a new document resets FAISS, chunk metadata, retrieval diagnostics, and chat history.

### Phase 3: Production Architecture

New structure:

```text
backend/
  api/
  services/
  rag/
  models/
  uploads/
  main.py

frontend/
  src/
    components/
    pages/
    services/
    App.jsx
```

Implemented APIs:

* `POST /upload`
* `POST /ask`
* `GET /stats`
* `GET /chat-history`
* `POST /clear-chat`

## Install

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install and run Ollama:

```bash
ollama pull llama3.2:3b
ollama serve
```

The first semantic indexing run downloads the `all-MiniLM-L6-v2` embedding model.

## Run Streamlit App

```bash
streamlit run app.py
```

## Run FastAPI Backend

```bash
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

## Run React Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

Set `VITE_API_URL` if the backend runs somewhere else.

## Migration Notes

* `pdf_processor.py` is the shared document and RAG engine used by both Streamlit and FastAPI.
* The old keyword retrieval path has been replaced by FAISS similarity search.
* Chat history is stored in process memory for now. Use a database or session store before deploying to multiple users.
* The FAISS index is process-local and single-document in this version. Re-upload documents after restarting the backend or Streamlit process.
* Uploaded files are saved under `uploads/` for Streamlit and `backend/uploads/` for FastAPI.
* DOC conversion still requires LibreOffice and the `soffice` command.

## Technologies

* Python
* Ollama
* Llama 3.2
* FastAPI
* Streamlit
* React
* Vite
* Axios
* sentence-transformers
* FAISS
* PyPDF
* python-docx
