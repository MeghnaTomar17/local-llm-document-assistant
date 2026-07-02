# Resume Intelligence Assistant

> A private, local-first ATS-style resume intelligence platform for uploading resumes, extracting candidate metadata, searching talent with natural language, chatting with individual resumes, and managing hiring decisions.

Resume Intelligence Assistant is built for recruiters who need speed, privacy, and control. It combines a FastAPI backend, React recruiter console, PostgreSQL persistence, local Ollama models, resume-aware chunking, FAISS retrieval, and deterministic validation into one practical hiring workflow.

The core idea is simple:

```text
Upload resumes -> Extract candidate data -> Review and verify -> Search candidates -> Chat with each resume -> decide next action
```

Everything important runs locally. Candidate resumes, extracted metadata, resume chunks, chat history, uploaded file blobs, and recruiter decisions are stored in PostgreSQL and local project storage. Local LLMs handle extraction and answering without sending sensitive candidate data to cloud APIs.

---

## What Makes It Stand Out

- Local-first AI resume processing with Ollama and Llama 3.2.
- Recruiter-focused React interface inspired by modern ATS tools.
- PostgreSQL-backed resume database with file blobs and editable metadata.
- Resume-aware chunking persisted in PostgreSQL for faster session reloads.
- Candidate-level isolated chat sessions, even when resumes were uploaded together.
- Natural-language recruiter search powered by validated SQL generation.
- HR decision workflow: Pending, On Hold, Accepted, Rejected.
- Smart duplicate detection using file hash, email, phone, name + email, and name + phone.
- Inline resume preview and direct download.
- Bulk folder processing for large resume datasets.
- Three independent recruiter note sections: HR Notes, Technical Notes, and Final Notes.

---

## Product Tour

### Dashboard

Get a clean overview of the candidate database:

- Total resumes
- Freshers
- Experienced candidates
- Verified candidates
- Needs review
- Accepted and rejected candidates
- Recent uploads

### Sessions

The Sessions page is the main recruiter workspace.

- Search candidates live from the left sidebar.
- Select a candidate and continue reviewing instantly.
- Upload one or multiple resumes.
- View the active resume summary table.
- Open the embedded Resume Workspace for the selected candidate.
- Preview, download, mark On Hold, accept, reject, edit metadata, add notes, and chat with the resume assistant.

### Resume Workspace

Each candidate has an isolated workspace:

- Candidate details and contact summary
- Fresher or experienced badge
- Verification badge
- HR decision badge
- Inline preview for PDFs
- Download fallback for DOCX or unsupported preview formats
- Resume, Chat, Metadata, and Notes tabs

### Recruiter Search

Ask simple recruiter questions and get matching candidates:

```text
Find Python developers in Bangalore
Show verified freshers with React skills
List experienced GIS candidates from Chennai
Show the latest uploaded resumes
```

Generated SQL is validated before execution, results are displayed in recruiter-friendly tables, and previous searches can be restored from history.

### Resume Chat

Ask questions about a selected candidate:

- "Summarize this resume"
- "Show technical skills"
- "What projects has this candidate worked on?"
- "Does this candidate have professional experience?"
- "Extract education details"

The assistant answers using retrieved resume chunks and keeps chat history isolated per candidate.

---

## Current Capabilities

### Resume Processing

Supported formats:

- PDF
- DOCX

Supported layouts:

- ATS resumes
- Multi-column resumes
- Designer resumes
- Academic resumes
- Professional resumes
- Scanned PDFs with OCR fallback

Processing pipeline:

```text
Upload
  -> Store on disk
  -> Store resume blob in PostgreSQL
  -> Extract text
  -> Assess extraction quality
  -> Extract metadata with local LLM
  -> Validate metadata deterministically
  -> Detect duplicates
  -> Chunk resume by logical sections once per unique resume
  -> Persist chunks
  -> Build FAISS index for chat
```

After the first upload, the assistant reloads resume chunks from PostgreSQL and rebuilds FAISS from stored chunk content. It does not parse or rechunk the original resume again unless the file content changes or an administrator explicitly reprocesses it.

### Metadata Extraction

Extracted fields include:

- Candidate name
- Email
- Phone number
- Skills
- Cities
- Fresher status
- HR decision
- HR Notes
- Technical Notes
- Final Notes

Recruiter-editable fields:

- Candidate name
- Email
- Phone number
- Skills
- Cities
- Fresher status
- HR Notes
- Technical Notes
- Final Notes
- HR decision

### Validation

The system combines local LLM extraction with deterministic cleanup:

- Rejects section headings as names
- Filters organization names
- Prevents email usernames from polluting candidate names
- Validates email patterns
- Normalizes phone numbers
- Rejects dates and years as phone numbers
- Preserves useful international phone formats
- Separates internships from professional employment for fresher detection

### Persistence

PostgreSQL is the source of truth for:

- Resume metadata
- Uploaded resume blob
- Stored file details
- Recruiter notes
- Verification state
- HR decision
- Resume chunks
- Chat history
- Search history
- Session records

Uploaded files are preserved both:

- On disk
- In PostgreSQL as `BYTEA`

---

## Architecture

```text
React Recruiter Console
        |
        v
FastAPI Routes
        |
        v
Service Layer
        |
        v
SQLAlchemy CRUD
        |
        v
PostgreSQL

Local AI Layer:
Ollama + Llama 3.2

Retrieval Layer:
Sentence Transformers + FAISS

Document Layer:
PyMuPDF + pdfplumber + pypdf + EasyOCR fallback
```

### Backend

- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- PostgreSQL
- Ollama integration
- Resume parsing and chunking
- FAISS retrieval
- Recruiter SQL search

### Frontend

- React 18
- Vite
- Axios
- Lucide icons
- ATS-style recruiter interface

### Local AI and Retrieval

- Ollama
- Llama 3.2
- Sentence Transformers
- all-MiniLM-L6-v2
- FAISS

---

## Repository Structure

```text
.
|-- backend/
|   |-- api/
|   |-- llm_sql/
|   |-- rag/
|   |-- routes/
|   |-- schemas/
|   `-- services/
|
|-- database/
|   |-- migrations/
|   |-- base.py
|   |-- connection.py
|   |-- crud.py
|   |-- init_db.py
|   `-- models.py
|
|-- frontend/
|   |-- src/
|   |   |-- components/
|   |   |-- context/
|   |   |-- hooks/
|   |   |-- pages/
|   |   |-- services/
|   |   `-- types/
|   |-- package.json
|   `-- tsconfig.json
|
|-- bulk_process.py
|-- pdf_processor.py
|-- requirements.txt
|-- roadmap.md
`-- README.md
```

---

## Setup

### 1. Clone

```bash
git clone <repository-url>
cd local-llm-document-assistant
```

### 2. Create Python Environment

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 4. Configure PostgreSQL

Create a database:

```sql
CREATE DATABASE resume_platform;
```

Create `.env` in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
```

Initialize tables:

```bash
python database/init_db.py
```

Apply migrations in order from `database/migrations/` if your database already exists or was created before the latest schema changes.

Current migration set includes support for:

- Resume blob storage
- Persistent sessions
- One session per resume
- Chat history
- Recruiter search history
- Resume chunks
- HR decisions including On Hold
- Split reviewer notes: HR Notes, Technical Notes, Final Notes

For an existing database, apply every file in `database/migrations/` in order, including:

```bash
psql -U postgres -d resume_platform -f database/migrations/010_extend_reviewer_workflow.sql
```

### 5. Configure Ollama

Install Ollama, then pull the local model:

```bash
ollama pull llama3.2:3b
```

Start Ollama:

```bash
ollama serve
```

---

## Running the App

### Backend

```bash
uvicorn backend.main:app --reload
```

Backend runs at:

```text
http://localhost:8000
```

Swagger docs:

```text
http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

---

## Bulk Resume Processing

Use the bulk processor to scan a folder recursively and ingest resumes without the web UI.

```bash
python bulk_process.py "<folder_path>"
```

Example:

```bash
python bulk_process.py "D:\Resume_Dataset"
```

Outputs:

| File | Purpose |
| --- | --- |
| `processing_report.csv` | Summary of processed resumes |
| `bulk_processing.log` | Detailed processing and error logs |

Bulk processing uses the same extraction, validation, duplicate detection, and persistence pipeline as the web app.

---

## API Overview

### Resume Management

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/upload` | Upload one resume |
| `POST` | `/upload-batch` | Upload multiple resumes |
| `GET` | `/resumes` | List recruiter-facing resume records |
| `GET` | `/resumes/{id}` | Get editable resume details |
| `PUT` | `/resumes/{id}` | Update editable metadata |
| `DELETE` | `/resumes/{id}` | Delete database record |
| `GET` | `/resumes/{id}/download` | Download stored resume |
| `GET` | `/resumes/{id}/preview` | Preview resume inline |
| `GET` | `/resumes/{id}/chunks` | Debug stored chunks |

### Sessions and Chat

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/sessions` | List resume workspaces |
| `POST` | `/switch-session` | Activate a workspace |
| `GET` | `/sessions/{id}/resumes` | List resumes in a workspace |
| `POST` | `/ask` | Ask questions about a resume |
| `GET` | `/chat-history` | Load chat history |
| `POST` | `/clear-chat` | Clear chat history |

### Recruiter Search

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/search` | Run natural-language candidate search |
| `GET` | `/search-history` | List previous searches |
| `DELETE` | `/search-history` | Clear all search history |
| `GET` | `/search-history/item/{id}` | Get one saved search |
| `DELETE` | `/search-history/{id}` | Delete one saved search |

---

## Recruiter Workflow

```text
1. Upload resumes
2. Review extracted candidate details
3. Edit metadata if needed
4. Open chat for a candidate
5. Ask resume-specific questions
6. Search the full database with recruiter questions
7. Preview or download resumes
8. Add HR, technical, and final notes
9. Mark candidates as pending, on hold, accepted, or rejected
```

---

## Data Privacy

The platform is designed for local and private operation:

- Resume text is processed locally.
- LLM calls use local Ollama models.
- Candidate data is stored in your PostgreSQL database.
- Uploaded files are stored locally and in PostgreSQL.
- Resume chunks are stored in PostgreSQL and reused for later chat sessions.
- No cloud LLM API is required.

---

## Development Checks

Backend syntax check:

```bash
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

Frontend production build:

```bash
cd frontend
npm run build
```

---

## Notes for Future Work

Strong next steps:

- Authentication and recruiter roles
- Audit logs for metadata edits and decisions
- Job description matching
- Candidate ranking
- Advanced filters
- Deployment scripts
- Automated migration runner
- Exportable recruiter shortlists

---

## Author

**Meghna Tomar**

AI, Machine Learning, NLP, FastAPI, React, PostgreSQL, Local LLMs

---

## License

Developed as part of an internship project for educational and research purposes.
