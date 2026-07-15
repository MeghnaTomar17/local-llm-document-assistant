# Resume Intelligence Assistant

> **A local-first, privacy-respecting recruiter intelligence console** for uploading candidate profiles, extracting structured metadata, analyzing competencies, searching talent in plain English, and executing resume-aware Q&A chat.

---

## Table of Contents
1. [Key Capabilities](#key-capabilities)
2. [Product & UI Overview](#product--ui-overview)
3. [System Architecture](#system-architecture)
4. [Recruiter Search Pipeline (8-Stage Flow)](#recruiter-search-pipeline-8-stage-flow)
5. [Resume Processing Pipeline](#resume-processing-pipeline)
6. [Explainable Fresher Detection](#explainable-fresher-detection)
7. [Repository Structure](#repository-structure)
8. [Setup & Configurations Summary](#setup--configurations-summary)
9. [API Reference](#api-reference)
10. [CLI Bulk Import Processor](#cli-bulk-import-processor)
11. [Verification & Code Diagnostics](#verification--code-diagnostics)
12. [Author & License](#author--license)

---

## Key Capabilities

* **Offline Local AI Execution**: Run advanced LLM parsing and retrieval-augmented generation (RAG) completely offline through Ollama. No external network requests are made, keeping sensitive candidate resumes secure.
* **8-Stage Search Engine**: Refactored recruiter search from an artificial ranker into a transparent, deterministic query builder. Stage-by-stage logs and live timing metrics are tracked directly.
* **Auto-Growing Search Console**: Recruiter search text area dynamically grows based on scroll height to accommodate full multi-paragraph Job Descriptions (JDs).
* **Segmented Pool Classifications**: Separate database profiles into `Internal Employee` or `External Candidate` pools to manage sourcing constraints efficiently.
* **Structured Decision-Making Workflow**: Review candidates, write categorized reviewer feedback (HR Notes, Technical Notes, Final Notes), mark profiles for interviews, and log definitive hire choices (Accepted, Rejected, On Hold, Pending).
* **Persistent Text Chunking**: Performs heavy document parsing, OCR fallbacks, and text chunking exactly once upon upload. Stores persistent chunks directly inside PostgreSQL to enable instant chat indexing upon subsequent reviews.
* **Dual Persistence Layer**: Uploaded documents are saved both as system files on disk and as direct SQL database blobs (`BYTEA` format) for robust backup.
* **Duplicate Profile Prevention**: Compares document checksums and candidate contact details during upload to reject repeated profiles.

---

## Product & UI Overview

### 1. Recruiter Dashboard
Displays database metrics at a glance:
* Total Resumes Uploaded
* Ratio of Freshers to Experienced Profiles
* Verified Candidate Counts
* Active Hiring Funnel (Accepted, Rejected, On Hold, Pending Review)
* Live feed of recently parsed candidate cards

### 2. Candidate Workspace & Resume Viewer
* **Interactive Resume Reader**: Renders direct PDF preview or provides safe docx download options.
* **Isolated Candidate Chat**: Discuss the candidate's background using FAISS similarity searches on the candidate's specific text chunks.
* **Metadata Editor**: Refine candidate details, skills list, and classification pools. Editing details automatically marks profiles as `Verified`.

### 3. Recruiter Search Page
Recruiters enter plain English search queries rather than constructing SQL manually:
* *“Find experienced React developers in Bangalore.”*
* *“Show me internal candidates with QGIS skills.”*
* *“List freshers marked for interview.”*

---

## System Architecture

```text
       ┌──────────────────────────────┐
       │   React Recruiter Console    │
       └──────────────┬───────────────┘
                      │ HTTP Rest Calls
                      ▼
       ┌──────────────────────────────┐
       │   FastAPI Web Backend Core   │
       └──────────────┬───────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐       ┌──────────────────┐
│   Local LLMs    │       │ PostgreSQL Store │
│ (via Ollama)    │       │                  │
│                 │       │ • Resumes        │
│ • Llama 3.2     │       │ • Metadata       │
│   (Extraction)  │       │ • Text Chunks    │
│ • Qwen 2.5      │       │ • Chat Logs      │
│   (Search NLU)  │       │ • Search History │
└─────────────────┘       └──────────────────┘
```

---

## Recruiter Search Pipeline (8-Stage Flow)

The recruiter search handles natural language requests through an 8-stage sequence to ensure transparency, security, and accuracy:

```text
┌─────────────────────────────────┐
│ 1. Cleaning                     │ --> Strips EEO/benefits/marketing templates
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 2. Requirement Extraction (LLM) │ --> LLM parses role, skills, fresher, and pool constraints
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 3. Skill Normalization          │ --> Canonicalizes skills via dictionary lookup
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 4. SQL Generation               │ --> Deterministically builds standard PostgreSQL query
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 5. SQL Validation               │ --> Validates syntax and filters out destructive statements
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 6. Database Retrieval           │ --> Executes query against database tables
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 7. Candidate Matching           │ --> Compares canonical skills and filters out zero-match rows
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ 8. API Response                 │ --> Returns results, parsed requirements, and stage timings
└─────────────────────────────────┘
```

---

## Resume Processing Pipeline

1. **Upload Request**: Parses multi-part file payloads (PDF, DOCX) and computes a SHA-256 file hash.
2. **Identity Verification**: Scans files for email or telephone matches in the database. Rejects duplicate uploads.
3. **Text Extraction**: Uses `PyMuPDF` / `pdfplumber` with fallback to `python-docx`. If no text is found, activates an `EasyOCR` fallback layer.
4. **Information Parsing**: Routes text to local Llama 3.2 model to pull contact info and skills.
5. **Resume Chunking**: Splits extracted text into semantic paragraphs (approx. 500 characters with 100 character overlap) and stores chunks permanently inside database tables.
6. **Workspace Creation**: Instantiates database entities for isolated candidate reviewer sessions.

---

## Explainable Fresher Detection

Candidate experience classification uses a deterministic, rule-based experience parser:
* **Freshers**: Candidates with zero professional industry experience. Internships, academic coursework, college capstones, research lab roles, and certifications do not qualify as professional experience.
* **Experienced**: Candidates who have worked in permanent, part-time, freelance, or consulting roles.
* **Heuristics**: Scans structural headers of parsed document structures (specifically searching for Experience / Employment titles) rather than applying general keyword scanning to ensure accuracy.

---

## Repository Structure

```text
.
├── backend/
│   ├── api/                   # REST API routes
│   │   └── routes.py          # Main endpoints index
│   ├── config/                # JSON dictionaries for skills normalization
│   ├── llm_sql/               # Recruiter search execution stages
│   ├── rag/                   # Vector space chunking & FAISS index
│   ├── routes/                # Main sub-routers wrapper
│   ├── schemas/               # API validation schemas
│   └── services/              # Base services layer
│
├── database/
│   ├── migrations/            # SQL database migrations
│   ├── base.py                # Base model declarations
│   ├── connection.py          # SQLAlchemy pool builder
│   ├── crud.py                # Database transactions
│   ├── init_db.py             # Database initial layout config
│   └── models.py              # Schema models (Resumes, Sessions, Chunks)
│
├── frontend/
│   ├── src/
│   │   ├── components/        # Recruiter widgets
│   │   ├── context/           # App context
│   │   ├── pages/             # App views (Dashboard, Search, Sessions)
│   │   ├── services/          # API network configurations
│   │   └── styles.css         # UI Design rules
│   ├── package.json
│   └── vite.config.ts
│
├── bulk_process.py            # Folder scanner CLI
├── pdf_processor.py           # Document parsing core
├── SETUP.md                   # Setup Manual
└── README.md                  # System Documentation
```

---

## Setup & Configurations Summary

*Detailed layout steps are provided in the [SETUP.md](SETUP.md) file.*

1. **Install Virtual Environment & Python Packages**:
   ```powershell
   python -m venv .venv
   # Windows
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Install Frontend Modules**:
   ```powershell
   cd frontend
   npm install
   cd ..
   ```
3. **Configure Environment Variables (`.env`)**:
   ```env
   DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
   OLLAMA_CHAT_MODEL=llama3.2:3b
   OLLAMA_SQL_MODEL=qwen2.5-coder:7b
   OLLAMA_HOST=http://localhost:11434
   ```
4. **Run DB Setup & Apply Migrations**:
   ```powershell
   python database/init_db.py
   # Run SQL migrations located in database/migrations/ in sequence.
   ```
5. **Verify AI Models**:
   ```powershell
   ollama pull llama3.2:3b
   ollama pull qwen2.5-coder:7b
   ```

---

## API Reference

### 1. Document Uploads

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Uploads and processes a single resume file (PDF or DOCX). |
| `POST` | `/upload-batch` | Uploads multiple resumes and provides live progress tracking metrics. |

### 2. Recruiter Workspaces

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/resumes` | Retrieves the list of all candidates in the database. |
| `GET` | `/resumes/{id}` | Fetches detailed candidate details and metadata. |
| `PUT` | `/resumes/{id}` | Updates candidate details. Editing metadata marks the profile as `Verified`. |
| `DELETE` | `/resumes/{id}` | Deletes candidate details and records. |
| `GET` | `/resumes/{id}/download` | Downloads the original file blob directly from PostgreSQL. |
| `GET` | `/resumes/{id}/preview` | Streams the document directly inside the preview frame. |

### 3. Recruiter Search Engine

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/search` | Executes an 8-stage natural language query builder search. |
| `GET` | `/search-history` | Loads the history of search terms. |
| `DELETE` | `/search-history` | Clears all search history records. |
| `DELETE` | `/search-history/{id}` | Deletes a single search record from history. |

### 4. Interactive RAG Chat

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ask` | Queries a candidate's resume text chunks. |
| `GET` | `/chat-history` | Loads candidate chat session history. |
| `POST` | `/clear-chat` | Resets chat session history. |

---

## CLI Bulk Import Processor

Import folders of resumes directly from the command line interface:

```powershell
python bulk_process.py "path/to/resume_folder" --candidate-type INTERNAL
```

### Options:
* `path/to/resume_folder`: System path containing resumes to scan.
* `--candidate-type`: Default candidate classification pool classification (`INTERNAL` or `EXTERNAL`).

### Export Outputs:
* `processing_report.csv`: CSV summary detailing upload metrics.
* `bulk_processing.log`: Execution log detailing performance metrics or extraction warnings.

---

## Verification & Code Diagnostics

Confirm build status by running syntax checkers before committing changes:

### Python syntax compilation
```powershell
python -m py_compile backend/main.py backend/api/routes.py backend/routes/resume_routes.py
```

### Frontend assets bundle compilation
```powershell
cd frontend
npm run build
cd ..
```

---

## Author & License

* **Developer**: Meghna Tomar
* **Role**: Software Engineering Intern (AI, RAG, and NLP development)
* **License**: Open-source workspace developed for internal research and ATS platform demonstration.
