# Resume Intelligence Assistant

> A local-first recruiter workspace for uploading resumes, extracting candidate details, searching talent in plain English, chatting with individual resumes, and tracking hiring decisions.

Resume Intelligence Assistant turns a folder of resumes into a private, searchable candidate database. It combines a FastAPI backend, React recruiter console, PostgreSQL persistence, local Ollama models, resume-aware chunking, FAISS retrieval, and recruiter-friendly workflows into one ATS-style application.

```text
Upload resumes -> Extract candidate data -> Review -> Search -> Chat -> Decide
```

No cloud LLM is required. Resume files, metadata, chunks, chat history, notes, and decisions stay on your machine and in your PostgreSQL database.

---

## Why It Stands Out

- Private local AI workflow using Ollama.
- Recruiter-friendly React interface with dashboard, sessions, resume workspace, and search.
- PostgreSQL source of truth for resumes, metadata, file blobs, chunks, notes, decisions, sessions, and search history.
- Uploaded resumes are stored both on disk and inside PostgreSQL as `BYTEA`.
- Candidate-level isolated resume workspaces and chat history.
- Natural-language recruiter search with SQL validation before execution.
- Resume-aware chunks are persisted once and reused later, avoiding repeated PDF parsing.
- Batch uploads show live per-resume progress.
- Duplicate detection prevents repeated candidate records.
- Editable metadata with verification status.
- HR decision workflow: Pending, On Hold, Accepted, Rejected.
- Split recruiter notes: HR Notes, Technical Notes, Final Notes.

---

## Product Overview

### Dashboard

See the health of the candidate database at a glance:

- Total resumes
- Freshers
- Experienced candidates
- Verified candidates
- Candidates needing review
- Accepted and rejected candidates
- Recent uploads

### Sessions

The main resume review area.

- Search candidates live from the sidebar.
- Upload one or many resumes.
- Watch batch upload progress resume by resume.
- Open one candidate workspace at a time.
- Review extracted details, preview the resume, download the original file, chat with the resume, and update hiring decisions.

### Resume Workspace

Each candidate has an individual workspace:

- Candidate profile and contact details
- Fresher or experienced status
- Verification status
- HR decision
- Resume preview or download fallback
- Resume chat
- Editable metadata
- HR, technical, and final notes

### Recruiter Search

Ask simple questions instead of writing SQL:

```text
Find Python developers in Bangalore
Show verified freshers with React skills
List experienced GIS candidates from Chennai
Show candidates currently on hold
Show the latest uploaded resumes
```

The backend generates SQL, validates it, runs it safely, and returns recruiter-friendly results. Search history can be shown or hidden from the UI.

### Resume Chat

Ask questions about the selected candidate only:

```text
Summarize this resume
Show technical skills
Extract contact details
What projects has this candidate worked on?
Does this candidate have professional experience?
```

The chat uses stored chunks for that candidate, rebuilds FAISS for retrieval, and keeps history isolated per resume.

---

## Processing Pipeline

```text
Resume upload
  -> Validate file type
  -> Store file on disk
  -> Store file bytes in PostgreSQL
  -> Extract text from PDF/DOCX
  -> Use OCR fallback when needed
  -> Extract metadata with local Ollama model
  -> Clean and validate metadata deterministically
  -> Detect duplicates
  -> Create resume-aware chunks
  -> Save chunks in PostgreSQL
  -> Build FAISS index for chat
  -> Create or update candidate workspace
```

When an existing resume workspace is opened later, the app loads chunks from PostgreSQL and rebuilds the FAISS index from stored chunk content. It skips PDF parsing and chunk generation when chunks already exist.

---

## Extracted Candidate Data

The system extracts and stores:

- Candidate name
- Email
- Phone number
- Skills
- Cities
- Fresher status
- Verification status
- Processing status
- Extraction status
- HR decision
- HR Notes
- Technical Notes
- Final Notes
- Uploaded file metadata
- Resume blob
- Resume chunks

Recruiters can edit:

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

Editing candidate metadata marks the resume as verified.

---

## Fresher Detection

The fresher classifier is deterministic and explainable:

- Fresher means no professional work experience.
- Internships, apprenticeships, academic projects, workshops, certifications, and college projects do not make a candidate experienced.
- Professional employment, contract work, consulting, freelance work, part-time work, or permanent roles make a candidate experienced.
- The logic focuses on experience/employment sections instead of keyword scanning the whole resume.

---

## Architecture

```text
React + Vite
    |
    v
FastAPI
    |
    v
Service Layer
    |
    v
SQLAlchemy 2.0
    |
    v
PostgreSQL

Local AI:
Ollama + Llama 3.2

Retrieval:
Sentence Transformers + FAISS

Document Parsing:
PyMuPDF + pdfplumber + pypdf + python-docx + EasyOCR fallback
```

---

## Tech Stack

### Backend

- FastAPI
- SQLAlchemy 2.0
- Pydantic v2
- PostgreSQL
- FAISS
- Sentence Transformers
- Ollama
- PyMuPDF, pdfplumber, pypdf, python-docx
- EasyOCR

### Frontend

- React
- Vite
- TypeScript
- Axios
- Lucide icons
- Custom ATS-style UI

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
|-- SETUP.md
`-- README.md
```

---

## Quick Start

For full installation and upgrade instructions, use [SETUP.md](SETUP.md).

### 1. Install Python Dependencies

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

### 3. Configure PostgreSQL

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
```

Create the database if needed:

```sql
CREATE DATABASE resume_platform;
```

Initialize tables:

```powershell
python database/init_db.py
```

Apply migrations in order from `database/migrations/` for existing databases.

### 4. Start Ollama

```powershell
ollama pull llama3.2:3b
ollama serve
```

### 5. Run Backend

```powershell
uvicorn backend.main:app --reload
```

Backend:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

### 6. Run Frontend

```powershell
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## API Highlights

### Resume Management

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/upload` | Upload one resume |
| `POST` | `/upload-batch` | Upload multiple resumes |
| `GET` | `/resumes` | List recruiter-facing resume records |
| `GET` | `/resumes/{id}` | Get editable resume metadata |
| `PUT` | `/resumes/{id}` | Update editable metadata |
| `DELETE` | `/resumes/{id}` | Delete database record only |
| `GET` | `/resumes/{id}/download` | Download resume from PostgreSQL blob |
| `GET` | `/resumes/{id}/preview` | Preview resume inline |
| `GET` | `/resumes/{id}/chunks` | Inspect stored chunks |

### Sessions and Chat

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/sessions` | List candidate workspaces |
| `POST` | `/switch-session` | Open a workspace |
| `GET` | `/sessions/{id}/resumes` | List resumes in a workspace |
| `POST` | `/ask` | Ask questions about a selected resume |
| `GET` | `/chat-history` | Load chat history |
| `POST` | `/clear-chat` | Clear chat history |

### Recruiter Search

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/search` | Search candidates with natural language |
| `GET` | `/search-history` | View recent searches |
| `DELETE` | `/search-history` | Clear search history |
| `GET` | `/search-history/item/{id}` | Restore one search |
| `DELETE` | `/search-history/{id}` | Delete one search |

---

## Bulk Processing

Process a folder of resumes without the web UI:

```powershell
python bulk_process.py "D:\Resume_Dataset"
```

Generated files:

| File | Purpose |
| --- | --- |
| `processing_report.csv` | Resume processing summary |
| `bulk_processing.log` | Detailed logs and errors |

Bulk processing uses the same extraction, validation, duplicate detection, and database persistence pipeline as the web app.

---

## Verification Commands

Backend syntax check:

```powershell
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

Frontend production build:

```powershell
cd frontend
npm run build
```

---

## Privacy

This project is designed for local recruiter workflows:

- Resume text is processed locally.
- Ollama runs locally.
- PostgreSQL stores candidate data locally.
- Uploaded files remain on disk and in the local database.
- No external LLM API is required.

---

## Future Improvements

- Authentication and recruiter roles
- Audit logs for metadata edits
- Job description matching
- Candidate ranking
- Exportable shortlists
- Automated migration runner
- Deployment scripts

---

## Author

**Meghna Tomar**

AI, Machine Learning, NLP, FastAPI, React, PostgreSQL, Local LLMs

---

## License

Developed as part of an internship project for educational and research purposes.
