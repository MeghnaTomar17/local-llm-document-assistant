# Setup Guide

This guide explains how to set up the current Resume Intelligence Assistant on a new PC or upgrade an older copy that only had the initial `resumes` table.

The app has three moving parts:

```text
PostgreSQL -> stores resumes, chunks, sessions, chat, notes, and search history
FastAPI    -> runs extraction, upload, chat, search, and resume APIs
React      -> recruiter dashboard and workspace
Ollama     -> local LLM used for metadata extraction and answers
```

---

## 1. Install Required Software

Install these first:

- Python 3.11 or newer
- Node.js 18 or newer
- PostgreSQL
- Ollama
- Git

Recommended checks:

```powershell
python --version
node --version
npm --version
psql --version
ollama --version
```

---

## 2. Get the Latest Project

Open PowerShell and go to the project folder.

If the project is already cloned:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant
git pull
```

If the project is being shared manually, copy the latest project folder to the PC and open PowerShell inside it.

---

## 3. Create the Python Environment

From the project root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

---

## 4. Install Frontend Packages

```powershell
cd frontend
npm install
cd ..
```

---

## 5. Prepare PostgreSQL

Start PostgreSQL and create the database if it does not already exist.

Open `psql` or pgAdmin and run:

```sql
CREATE DATABASE resume_platform;
```

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
```

Replace `<password>` with the local PostgreSQL password.

Example:

```env
DATABASE_URL=postgresql://postgres:admin123@localhost:5432/resume_platform
```

---

## 6. Back Up Existing Data

If this PC already has resume data, take a backup before migrations:

```powershell
pg_dump -U postgres -d resume_platform -f resume_platform_backup.sql
```

Keep this file safe until setup is verified.

---

## 7. Create Base Tables

Run:

```powershell
python database/init_db.py
```

This creates missing tables from the SQLAlchemy models. It does not intentionally delete existing data.

---

## 8. Apply Database Migrations

Run all migrations in order.

```powershell
psql -U postgres -d resume_platform -f database/migrations/001_add_resume_blob.sql
psql -U postgres -d resume_platform -f database/migrations/002_add_persistent_sessions.sql
psql -U postgres -d resume_platform -f database/migrations/003_one_session_per_unique_resume.sql
psql -U postgres -d resume_platform -f database/migrations/004_sync_session_schema.sql
psql -U postgres -d resume_platform -f database/migrations/004_workspace_chat_and_search_history.sql
psql -U postgres -d resume_platform -f database/migrations/005_create_recruiter_search_history.sql
psql -U postgres -d resume_platform -f database/migrations/005_isolate_resume_sessions.sql
psql -U postgres -d resume_platform -f database/migrations/006_decouple_recruiter_search_history.sql
psql -U postgres -d resume_platform -f database/migrations/007_create_resume_chunks.sql
psql -U postgres -d resume_platform -f database/migrations/008_add_resume_chunks_unique_constraint.sql
psql -U postgres -d resume_platform -f database/migrations/009_add_hr_decision.sql
psql -U postgres -d resume_platform -f database/migrations/010_extend_reviewer_workflow.sql
```

These migrations add:

- Resume file blob storage
- Persistent recruiter sessions
- Candidate-level resume workspaces
- Chat history
- Recruiter search history
- Resume chunks
- Unique chunk protection
- HR decisions
- On Hold decision status
- HR Notes, Technical Notes, and Final Notes

If PostgreSQL says a column, index, or table already exists, continue with the next migration unless the command stops with a serious error.

---

## 9. Install and Start Ollama

Pull the model:

```powershell
ollama pull llama3.2:3b
```

Start Ollama:

```powershell
ollama serve
```

Keep this window open while using the app.

If Ollama says it is already running, that is fine.

---

## 10. Start the Backend

Open a new PowerShell window:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

---

## 11. Start the Frontend

Open another PowerShell window:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant\frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

Open that URL in the browser.

---

## 12. Verify the App

Check these after setup:

- Dashboard opens.
- Sessions page opens.
- Existing resumes appear.
- Candidate search in the Sessions sidebar works.
- Uploading one PDF or DOCX works.
- Uploading a batch shows progress like `2 of 8`, `3 of 8`.
- Metadata appears after upload.
- Editing candidate details saves to PostgreSQL.
- Page refresh keeps edited metadata.
- HR decision buttons show only On Hold, Accept, and Reject.
- Pending is shown as the default decision state.
- HR Notes, Technical Notes, and Final Notes save correctly.
- Resume preview opens for PDFs.
- Resume download works from the PostgreSQL blob.
- Chat answers only for the selected candidate.
- Reopening a resume uses stored chunks instead of parsing the PDF again.
- Recruiter Search returns candidate results.
- Search history can be hidden or shown.

---

## Useful Commands

Backend syntax check:

```powershell
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

Frontend production build:

```powershell
cd frontend
npm run build
```

Process resumes from a folder:

```powershell
python bulk_process.py "D:\Resume_Dataset"
```

---

## Troubleshooting

### Frontend cannot connect to backend

Make sure the backend is running:

```text
http://localhost:8000
```

Also check that `frontend/src/services/http.ts` points to the correct backend URL or that `VITE_API_URL` is set correctly.

### Backend says a database column does not exist

Run the migrations from step 8 again in order.

Common missing columns usually come from skipped migrations:

- `resume_blob`
- `chat_history`
- `resume_id`
- `hr_decision`
- `hr_notes`
- `technical_notes`
- `final_notes`

### Upload works but chat has no context

Check that chunks exist:

```sql
SELECT resume_id, COUNT(*)
FROM resume_chunks
GROUP BY resume_id;
```

New uploads should create chunks automatically. Existing older resumes can still fall back to the older path when needed.

### Ollama extraction or chat fails

Confirm Ollama is running:

```powershell
ollama list
```

If the model is missing:

```powershell
ollama pull llama3.2:3b
```

### Python dependencies fail

Use Python 3.11+, activate the virtual environment, then reinstall:

```powershell
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Node dependencies fail

From the frontend folder:

```powershell
npm install
```

If needed:

```powershell
npm cache verify
```

---

## Expected Daily Startup

After setup is complete, daily startup is simple.

Terminal 1:

```powershell
ollama serve
```

Terminal 2:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant
.\venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```

Terminal 3:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant\frontend
npm run dev
```

Then open:

```text
http://localhost:5173
```
