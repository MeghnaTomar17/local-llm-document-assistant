# Setup & Deployment Guide

Follow this step-by-step guide to set up the Resume Intelligence Assistant on any new system.

---

## 📋 System Prerequisites

Before starting, install the following software dependency runtimes:

1. **Python (v3.11 or newer)**: [Download Python](https://www.python.org/downloads/) (Make sure to check "Add Python to PATH" during installation).
2. **Node.js (v18 or newer)**: [Download Node.js](https://nodejs.org/) (Includes the `npm` package manager).
3. **PostgreSQL (v15 or newer)**: [Download PostgreSQL](https://www.postgresql.org/download/) (Remember the password you set for the default `postgres` user during setup).
4. **Ollama**: [Download Ollama](https://ollama.com/) (Used to run local AI models offline).
5. **Git**: [Download Git](https://git-scm.com/downloads) (Optional, for cloning).

Verify your installed versions:
```powershell
python --version
node --version
npm --version
psql --version
ollama --version
```

---

## 🚀 Step-by-Step Installation

### Step 1: Navigate to Project Directory
Open your shell (PowerShell on Windows, Terminal on macOS/Linux) and navigate to the project directory:
```powershell
cd path/to/local-llm-document-assistant
```

### Step 2: Configure Python Virtual Environment

#### 💻 Windows (PowerShell)
1. If your system blocks script execution, temporarily enable script running:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
   ```
2. Create and activate the virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

#### 🍎 macOS / Linux
1. Create and activate the virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   python3 -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Step 3: Install Frontend Node Packages
Navigate to the frontend folder, download client-side modules, and return:
```powershell
cd frontend
npm install
cd ..
```

### Step 4: Configure PostgreSQL Database
1. Open your PostgreSQL terminal client (`psql`) or PGAdmin.
2. Execute the following SQL query to create a clean database:
   ```sql
   CREATE DATABASE resume_platform;
   ```
3. Create a configuration file named `.env` in the project root folder (`local-llm-document-assistant/.env`) and copy the template below. Replace `<your_password>` with your PostgreSQL password:

```env
DATABASE_URL=postgresql://postgres:<your_password>@localhost:5432/resume_platform
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_SQL_MODEL=qwen2.5-coder:7b
OLLAMA_MODEL=llama3.2:3b
OLLAMA_METADATA_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434
```

### Step 5: Initialize Database Schema & Run Migrations
Generate the tables and apply the database migrations in order:

```powershell
# 1. Initialize core tables:
python database/init_db.py

# 2. Run schema upgrade migrations (replace 'postgres' with your PostgreSQL username if different):
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

### Step 6: Download Local AI Models
Start your local Ollama application and download the necessary neural network models:
```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
```
Verify the models are pulled successfully:
```powershell
ollama list
```

---

## 💻 Daily Startup Guide

To launch the system daily, start these components in three separate terminals:

### Terminal 1: Ollama Model Runner
```powershell
ollama serve
```

### Terminal 2: FastAPI Backend Server
```powershell
# Navigate to project root, activate virtual environment, and run:
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload
```
*Your interactive Swagger API documentation is available at:* **[http://localhost:8000/docs](http://localhost:8000/docs)**

### Terminal 3: React Recruiter Console
```powershell
# Navigate to the frontend directory and start the dev server:
cd frontend
npm run dev
```
*Your local recruiter web interface is available at:* **[http://localhost:5173](http://localhost:5173)**

---

## 🛠️ Verification & Diagnostics

To confirm everything compiles and runs correctly before using the app, run these checks:

### 1. Backend python syntax compilation
```powershell
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

### 2. Frontend production assets build compilation
```powershell
cd frontend
npm run build
cd ..
```

---

## ❓ Troubleshooting

### "Script execution is disabled on this system" (Windows)
Open PowerShell as Administrator and run the following command to allow local scripts to execute:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

### Database connection failures
If Uvicorn crashes reporting `sqlalchemy.exc.OperationalError: Connection refused`, check that:
1. The PostgreSQL server is running.
2. The database password in your `.env` file does not contain unescaped special characters.
3. The database `resume_platform` was created.

### Resume chat has no context or fails
If candidate chat doesn't return responses, check that chunks are being written to the database:
```sql
SELECT resume_id, COUNT(*) FROM resume_chunks GROUP BY resume_id;
```
For old resume uploads, re-uploading the files will automatically parse, chunk, and index them.
