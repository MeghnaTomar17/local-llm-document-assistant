# Setup Guide

This guide explains how to set up the Resume Intelligence Assistant on a new PC or upgrade an existing workspace.

The application architecture has three moving parts:

```text
PostgreSQL  -> Persistence for resumes, file blobs, chunks, sessions, chat history, and search logs.
FastAPI     -> Backend processing for extraction, upload, chat, and recruiter search.
React       -> Frontend recruiter console with dashboards, workspaces, and search pages.
Ollama      -> Local AI models running completely offline.
```

---

## Prerequisites

Before starting, install the following software on your system:

- **Python 3.11** or newer
- **Node.js 18** or newer
- **PostgreSQL** (version 15 or newer recommended)
- **Ollama** (latest stable release)
- **Git**

Verify your environment by running:

```powershell
python --version
node --version
npm --version
psql --version
ollama --version
```

---

## 1. Setup the Codebase

Clone the repository or extract the project folder, then navigate into the project root directory in your shell:

```powershell
cd path/to/local-llm-document-assistant
```

---

## 2. Configure Python Virtual Environment

Create and activate a virtual environment (`.venv`) to manage dependencies locally:

### Windows (PowerShell)
```powershell
python -m venv .venv
# If script execution is blocked, run: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 3. Install Frontend Packages

Navigate to the frontend folder, install npm dependencies, and return:

```powershell
cd frontend
npm install
cd ..
```

---

## 4. Set Up PostgreSQL Database

1. Ensure PostgreSQL is running.
2. Open your terminal database client (`psql`) or PGAdmin and run the following command to create the application database:

```sql
CREATE DATABASE resume_platform;
```

3. Create a `.env` file in the project root folder. Copy the template below and replace `<password>` with your database credentials:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_SQL_MODEL=qwen2.5-coder:7b
OLLAMA_MODEL=llama3.2:3b
OLLAMA_METADATA_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434
```

---

## 5. Initialize Schema & Apply Migrations

1. Run the database initializer to build the tables:

```powershell
python database/init_db.py
```

2. Run the database migrations in order to add all necessary recruiter search and session tracking schemas:

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
psql -U postgres -d resume_platform -f database/migrations/011_add_interview_marked.sql
psql -U postgres -d resume_platform -f database/migrations/012_add_candidate_type.sql
```

---

## 6. Configure Ollama Models

Pull the required AI models to run them locally:

```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
```

Make sure the Ollama application is running. You can check model availability by typing:

```powershell
ollama list
```

---

## 7. Start the Application

To run the application, open three separate terminal windows:

### Terminal 1: Start Ollama
```powershell
ollama serve
```

### Terminal 2: Start Backend Server
```powershell
# Navigate to project root, activate virtual environment, and run:
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```
*API Swagger Docs will be available at: http://localhost:8000/docs*

### Terminal 3: Start React Frontend
```powershell
# Navigate to the frontend folder and run:
cd frontend
npm run dev
```
*Frontend Console will be available at: http://localhost:5173*

---

## 8. Verification & Diagnostics

Verify your setup by running the compiler check on Python modules and Vite:

### Backend syntax compiler check
```powershell
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

### Frontend build verification
```powershell
cd frontend
npm run build
cd ..
```

---

## Troubleshooting

- **Database Column Errors**: If you encounter errors regarding missing database columns (`interview_marked`, `candidate_type`, `hr_decision`), confirm that you ran all migrations in Step 5 in correct alphabetical sequence.
- **Port Conflict (8000/5173)**: If Uvicorn or Vite fail to start due to port conflicts, make sure no old processes are running in the background. On Windows, you can kill stuck tasks via:
  ```powershell
  Stop-Process -Name python, uvicorn -Force -ErrorAction SilentlyContinue
  ```
- **Llama Candidate Pool defaulting to INTERNAL**: If natural language queries default the search pool to `INTERNAL`, pull the latest extraction prompts from the repository to enable keyword-dependent classification.
