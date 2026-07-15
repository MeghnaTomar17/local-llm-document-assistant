# Resume Intelligence Assistant

> A local-first recruiter workspace for uploading resumes, extracting candidate details, searching talent in plain English, chatting with individual resumes, and tracking hiring decisions.

Resume Intelligence Assistant turns a folder of resumes into a private, searchable candidate database. It combines a FastAPI backend, React recruiter console, PostgreSQL database persistence, offline Ollama models, resume-aware chunking, FAISS retrieval, and developer-friendly workflows into one ATS-style application.

```text
Upload Resumes -> Extract Candidate Metadata -> Review Profile -> Search Pool -> Chat Workspace -> Update Hiring Decisions
```

No cloud LLM is required. Resume files, metadata, text chunks, chat history, notes, and decisions stay entirely on your local machine and in your PostgreSQL database.

---

## Core Capabilities

- **Private Offline AI**: Metadata extraction and chat run locally on your system using Ollama.
- **Dedicated Task-Based Routing**:
  - **Llama 3.2** for candidate info extraction and document Q&A chat.
  - **Qwen2.5-Coder** for structured search query interpretation.
- **Precision Recruiter Search**: Ask natural language questions instead of writing SQL queries. Uses an 8-stage pipeline with EEO/Boilerplate cleaning, deterministic SQL generation, query validation, multi-level fallbacks, and strict python skill-matching.
- **Auto-Growing Textarea & Key Shortcuts**: Paste full job descriptions directly; uses scroll height auto-resizing and `Ctrl + Enter` to search.
- **Search Progress Tracker**: Live progress displays active extraction steps (`Cleaning requirements...`, `Generating SQL...`, etc.) with status marks.
- **Candidate Pool Classification**: Classifies and filters candidates into `Internal` employees or `External` vendor profiles.
- **Interview & HR Decisions**: Track candidates with status flags (Marked for Interview vs Review) and structured decisions (Accepted, Rejected, On Hold) with distinct reviewer notes (HR, Technical, Final).
- **Persistent Text Chunking**: Text parsing and FAISS indexing occur once upon upload, saving results directly to PostgreSQL to prevent parsing documents repeatedly.
- **Explainable Fresher Check**: Evaluates candidates' work history sections to determine experienced vs fresher profiles, ignoring academic projects and internships.

---

## Tech Stack

### Backend
- **FastAPI** - REST API routes
- **SQLAlchemy 2.0** - PostgreSQL ORM
- **PostgreSQL** - Relational data store
- **FAISS & Sentence Transformers** - Semantic text retrieval
- **PyMuPDF, pdfplumber, python-docx** - Document text extraction
- **Ollama** - Offline LLM runtime

### Frontend
- **React + Vite** - Development bundler and frontend framework
- **TypeScript** - Strict typing safety
- **Vanilla CSS** - Premium, responsive recruiter layouts
- **Lucide React** - UI Icons

---

## Project Structure

```text
.
├── backend/
│   ├── api/             # REST endpoints
│   ├── config/          # Skill dictionaries
│   ├── llm_sql/         # Recruiter Search Pipeline
│   ├── rag/             # Document Chat (FAISS / RAG)
│   ├── routes/          # API router setup
│   ├── schemas/         # Pydantic models
│   └── services/        # Business logic services
│
├── database/
│   ├── migrations/      # DB Schema upgrades
│   ├── base.py
│   ├── connection.py
│   ├── crud.py
│   ├── init_db.py
│   └── models.py
│
├── frontend/
│   ├── src/
│   │   ├── components/  # Layout blocks
│   │   ├── context/     # React state store
│   │   ├── pages/       # Dashboards & search pages
│   │   ├── services/    # Client API connectors
│   │   └── types/       # TypeScript declarations
│   ├── package.json
│   └── tsconfig.json
│
├── bulk_process.py      # Folder processing utility
├── pdf_processor.py     # Resume parsing core
├── SETUP.md             # Installation manual
└── README.md            # Product overview
```

---

## Quick Start Overview

*Refer to [SETUP.md](SETUP.md) for step-by-step setup details.*

1. **Start PostgreSQL and create database**:
   ```sql
   CREATE DATABASE resume_platform;
   ```
2. **Pull Ollama Models & Run**:
   ```powershell
   ollama pull llama3.2:3b
   ollama pull qwen2.5-coder:7b
   ollama serve
   ```
3. **Configure Environment (`.env`)**:
   ```env
   DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
   OLLAMA_CHAT_MODEL=llama3.2:3b
   OLLAMA_SQL_MODEL=qwen2.5-coder:7b
   ```
4. **Init Database & Run Backend**:
   ```powershell
   python database/init_db.py
   # Apply migrations inside database/migrations/
   uvicorn backend.main:app --reload
   ```
5. **Run React Frontend**:
   ```powershell
   cd frontend
   npm run dev
   ```

---

## API Summary

### Resume Profiles & Workspace
- `POST /upload` - Parse and save a single resume file.
- `POST /upload-batch` - Upload multiple resumes with progress tracking.
- `GET /resumes` - Retrieve list of resumes.
- `GET /resumes/{id}` - Load candidate details.
- `PUT /resumes/{id}` - Save edited details.
- `PATCH /resumes/{id}/interview` - Toggle interview marked status.
- `PATCH /resumes/{id}/candidate-type` - Update pool classification.
- `GET /resumes/{id}/download` - Download candidate resume file.
- `GET /resumes/{id}/preview` - Preview document inline.

### Search and Chat
- `POST /search` - Run 8-stage natural language candidate retrieval.
- `GET /search-history` - Load recent search logs.
- `POST /ask` - Query the selected candidate's resume (RAG).
- `GET /chat-history` - Retrieve isolated chat logs.

---

## Folder Bulk Import

Process a directory of resumes directly via command line (INTERNAL or EXTERNAL classification):

```powershell
python bulk_process.py "path/to/folder" --candidate-type INTERNAL
```

This updates database schema tables directly and exports processing summaries to `processing_report.csv`.
