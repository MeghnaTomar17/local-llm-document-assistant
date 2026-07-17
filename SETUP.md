# 🚀 Complete Setup & Installation Guide

This guide is designed to help anyone set up the **Resume Intelligence Assistant** on their local machine from scratch. Follow the steps sequentially to get the application up and running.

---

## 📋 Table of Contents
1. [Runtimes & Prerequisites](#1-runtimes--prerequisites)
2. [Step-by-Step Setup](#2-step-by-step-setup)
   - [Clone / Navigate to Folder](#step-1-navigate-to-project-folder)
   - [Setup Virtual Environment](#step-2-setup-python-virtual-environment)
   - [Install Frontend Packages](#step-3-install-frontend-packages)
   - [Create & Configure PostgreSQL](#step-4-create--configure-postgresql)
   - [Initialize Schema (Fresh vs Upgrade)](#step-5-initialize-database-schema)
   - [Download Local LLMs](#step-6-configure-ollama-local-llms)
3. [Running the Application](#3-running-the-application)
4. [Verification & Verification Checks](#4-verification--verification-checks)
5. [Troubleshooting Guide (Common Issues)](#5-troubleshooting-guide)

---

## 1. Runtimes & Prerequisites

Before configuring the project, make sure to download and install the following software dependency runtimes.

| Dependency | Purpose | Download Link |
|---|---|---|
| **Python 3.11+** | Runs the FastAPI backend server | [Download Python](https://www.python.org/downloads/) |
| **Node.js 18+** | Builds and runs the React frontend console | [Download Node.js](https://nodejs.org/) |
| **PostgreSQL 15+** | Relational database to store resumes and metadata | [Download PostgreSQL](https://www.postgresql.org/download/) |
| **Ollama** | Local runtime environment for offline LLMs | [Download Ollama](https://ollama.com/) |

### 🔍 Verification Checklist
Verify that your system recognizes all required CLI tools by running these commands in your terminal:
```powershell
python --version
node --version
npm --version
psql --version
ollama --version
```
> ⚠️ **Windows Warning**: During Python installation, make sure to check **"Add Python to PATH"** at the bottom of the installer window. If you skip this, your terminal will report `python is not recognized`.

---

## 2. Step-by-Step Setup

### Step 1: Navigate to Project Folder
Open your terminal (PowerShell on Windows, Terminal on macOS/Linux) and navigate to the project directory:
```powershell
cd path/to/local-llm-document-assistant
```

---

### Step 2: Setup Python Virtual Environment

A virtual environment isolates project dependencies, preventing version conflicts with other software on your PC.

#### 💻 Windows (PowerShell)
1. If Windows blocks script execution, allow local scripts to run temporarily:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
   ```
2. Create the virtual environment folder:
   ```powershell
   python -m venv .venv
   ```
3. Activate the environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
   *(You should now see `(.venv)` in front of your terminal command prompt)*
4. Install all python requirements:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

#### 🍎 macOS / Linux
1. Create the virtual environment folder:
   ```bash
   python3 -m venv .venv
   ```
2. Activate the environment:
   ```bash
   source .venv/bin/activate
   ```
   *(You should now see `(.venv)` in front of your terminal command prompt)*
3. Install all python requirements:
   ```bash
   python3 -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

### Step 3: Install Frontend Packages
Open a separate terminal shell or use the same one to install the React user interface modules:
```powershell
cd frontend
npm install
cd ..
```

---

### Step 4: Create & Configure PostgreSQL

#### 1. Create the Database
* **Using pgAdmin (GUI)**:
  1. Open pgAdmin and connect to your local server.
  2. Right-click **Databases** -> **Create** -> **Database...**
  3. Enter `resume_platform` in the Database field and click **Save**.
* **Using Command Line**:
  Open a terminal and execute:
  ```powershell
  createdb -U postgres resume_platform
  ```

#### 2. Create the Environment File
Create a new file named `.env` in the root folder of the project (`local-llm-document-assistant/.env`) and copy the template below. Replace `<your_password>` with your PostgreSQL account password:

```env
DATABASE_URL=postgresql://postgres:<your_password>@localhost:5432/resume_platform
OLLAMA_CHAT_MODEL=llama3.2:3b
OLLAMA_SQL_MODEL=qwen2.5-coder:7b
OLLAMA_MODEL=llama3.2:3b
OLLAMA_METADATA_MODEL=llama3.2:3b
OLLAMA_HOST=http://localhost:11434
```

---

### Step 5: Initialize Database Schema

Choose **one** of the two options below depending on your database state:

#### Option A: Fresh Database Installation (Standard)
If you have just created a blank database, initialize all system tables automatically:
```powershell
python database/init_db.py
```
*Expected output:*
```text
Creating database tables...
Done!
```
*(No further migrations are needed, as this builds the latest tables including interview flags and pool fields).*

#### Option B: Upgrading an Existing Database Workspace
If you have a database containing records from a previous version of the app and want to upgrade the schemas without losing your uploaded resumes, you can either:

**1. Run migrations automatically using the Python runner (Recommended):**
```powershell
python database/run_migrations.py
```

**2. Alternatively, apply individual migrations manually via the psql CLI:**
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
*(Replace `postgres` with your local PostgreSQL role username if it is configured differently).*

---

### Step 6: Configure Ollama Local LLMs
Make sure the Ollama application is running (you should see the Ollama icon in your taskbar/menu tray). Open your terminal and pull the models:

```powershell
ollama pull llama3.2:3b
ollama pull qwen2.5-coder:7b
```
Verify they were downloaded successfully by listing the models:
```powershell
ollama list
```
*Expected output should show:*
* `llama3.2:3b`
* `qwen2.5-coder:7b`

---

## 3. Running the Application

To run the application, open **three separate terminal windows**:

### Terminal 1: Ollama Server
Start the local AI model inference engine:
```powershell
ollama serve
```

### Terminal 2: FastAPI Backend
Start the Python REST api:
```powershell
# Windows
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload

# macOS / Linux
source .venv/bin/activate
uvicorn backend.main:app --reload
```
*Expected output: `INFO: Uvicorn running on http://127.0.0.1:8000`*

### Terminal 3: React Frontend Console
Start the React user interface development server:
```powershell
cd frontend
npm run dev
```
*Expected output: `  VITE v6.4.3  ready in ... ms`*

---

## 4. Verification & Verification Checks

To make sure your installation was fully successful, perform the following verification checks:

1. **Verify Backend API**: Open **[http://localhost:8000/docs](http://localhost:8000/docs)** in your web browser. You should see the interactive Swagger API documentation.
2. **Verify Frontend UI**: Open **[http://localhost:5173](http://localhost:5173)** in your browser. You should see the Recruiter Workspace Dashboard.
3. **Syntax Checks**: To confirm that all Python scripts compile without syntax errors:
   ```powershell
   python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
   ```
4. **Vite Build Check**: Verify that frontend code compiles successfully for production deployment:
   ```powershell
   cd frontend
   npm run build
   cd ..
   ```

---

## 5. Troubleshooting Guide

### ❌ Python / Pip command not found
* **Solution**: Ensure Python was added to your PATH environment variables during installation. Try restarting your terminal, or reinstall Python checking the "Add Python to PATH" box.

### ❌ Windows Blocks Virtual Environment Activation
If you get a red error stating script execution is disabled on this system:
* **Solution**: Run this command in PowerShell to grant execution permissions for the current user:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
  ```

### ❌ `OperationalError: Connection refused` / Database Error
* **Solution**: Check that your PostgreSQL service is running on your machine. Confirm that the password you set during PostgreSQL installation matches the password written in your `.env` file.

### ❌ Uvicorn / Vite Ports (8000 / 5173) are already in use
* **Solution**: Kill any stale background processes running on your system. On Windows, run:
  ```powershell
  Stop-Process -Name python, uvicorn -Force -ErrorAction SilentlyContinue
  ```

### ❌ LLM Chats / Summaries return empty values
* **Solution**: Ensure Ollama is running and that the model names in your `.env` match the models outputted by `ollama list`.
