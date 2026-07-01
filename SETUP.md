# Setup Guide

This guide is for setting up the project on a PC that may already have the older version of the database with only the initial `resumes` table.

## 1. Update the Project

Open PowerShell in the project folder:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant
git pull
```

If the project is being copied manually instead of using Git, replace the old folder with the latest project folder.

## 2. Create or Activate Python Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

## 4. Check PostgreSQL

Make sure PostgreSQL is running.

The project needs a `.env` file in the project root:

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
```

Replace `<password>` with the PostgreSQL password.

If the database does not exist yet, create it:

```sql
CREATE DATABASE resume_platform;
```

## 5. Backup the Existing Database

Before applying migrations, take a backup:

```powershell
pg_dump -U postgres -d resume_platform -f resume_platform_backup.sql
```

This keeps the existing resume data safe.

## 6. Create Any Missing Base Tables

Run:

```powershell
python database/init_db.py
```

This creates missing tables from the current SQLAlchemy models. It does not delete existing data.

## 7. Apply Database Migrations

Run these migrations in order:

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
```

If a migration says something already exists, that is usually fine. Continue with the remaining migrations.

## 8. Start Ollama

Install Ollama if it is not installed, then run:

```powershell
ollama pull llama3.2:3b
ollama serve
```

Keep Ollama running while using the app.

## 9. Start Backend

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

## 10. Start Frontend

Open another PowerShell window:

```powershell
cd D:\internship-hexamap\project-one\local-llm-document-assistant\frontend
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## 11. Quick Verification

Check these things after setup:

- Dashboard opens.
- Sessions page loads.
- Existing resumes appear.
- Uploading a PDF or DOCX works.
- Candidate metadata is saved.
- Editing candidate details updates after refresh.
- Chat works for one selected candidate only.
- Recruiter Search returns results.
- Resume download works.

## Troubleshooting

If the backend says a database column is missing, re-run the migrations from step 7.

If the frontend cannot connect, confirm the backend is running at `http://localhost:8000`.

If chat or extraction fails, confirm Ollama is running and `llama3.2:3b` is installed.

If dependencies fail to install, check Python, Node.js, npm, and PostgreSQL are installed correctly.
