````markdown
# Resume Intelligence Platform

> A fully local, AI-powered Resume Intelligence Platform built using **FastAPI**, **React**, **PostgreSQL**, **Ollama**, **Llama 3.2**, **FAISS**, and **Sentence Transformers**.

The Resume Intelligence Platform is designed to automate resume processing, metadata extraction, persistent storage, recruiter management, and semantic retrieval while ensuring complete data privacy through locally hosted Large Language Models (LLMs).

Unlike cloud-based resume parsing solutions, all document processing, metadata extraction, and inference are performed locally using Ollama, ensuring that sensitive candidate information never leaves the local system.

---

# Features

## Resume Upload & Processing

- Upload PDF and DOCX resumes.
- Support for ATS-friendly resumes, Canva resumes, designer resumes, and multi-column layouts.
- Multi-stage document extraction pipeline:
  - PyMuPDF
  - pdfplumber
  - pypdf
  - EasyOCR (fallback)
- Automatic extraction quality assessment.
- Resume-aware section detection.
- Resume-aware chunking.
- Duplicate resume detection using SHA256 hashing.

---

## AI Metadata Extraction

The platform combines Local LLM reasoning with deterministic validation to generate accurate candidate metadata.

### Extracted Metadata

- Candidate Name
- Email Address
- Phone Number
- Technical Skills
- Cities / Locations
- Fresher Status

### Validation Pipeline

Candidate metadata passes through multiple validation layers before storage.

#### Candidate Name

- Section heading rejection
- Organization filtering
- Email username contamination prevention
- Uppercase normalization
- Initial handling
- Multi-word name support

#### Email

- Pattern validation
- Invalid email rejection
- Automatic fallback

#### Phone Number

- Country code support
- Leading zero preservation
- Invalid number filtering
- Date/year rejection
- International number handling

---

# Resume Persistence

Unlike earlier prototype versions, metadata is now stored permanently in PostgreSQL.

Each uploaded resume generates a persistent database record containing:

- UUID
- SHA256 Resume Hash
- Original Filename
- Stored Filename
- File Path
- MIME Type
- Resume Binary (BYTEA)
- Candidate Metadata
- Recruiter Notes
- Processing Status
- Extraction Status
- Verification Status
- Upload Timestamp
- Last Updated Timestamp

Uploaded resumes are stored:

- On Disk
- Inside PostgreSQL (BYTEA)

PostgreSQL serves as the application's **single source of truth**.

---

# Recruiter Management

The platform includes recruiter-oriented CRUD functionality.

Supported operations include:

- View all resumes
- View individual resume
- Edit extracted metadata
- Download uploaded resume
- Delete candidate record

Recruiters can modify:

- Candidate Name
- Email
- Phone Number
- Skills
- Cities
- Fresher Status
- Notes

After recruiter verification:

- `is_verified = true`
- `updated_at` is automatically updated.

---

# Resume-Aware Chunking

Instead of fixed-size text chunks, resumes are divided into logical sections.

Supported sections include:

- Contact Information
- Professional Summary
- Education
- Skills
- Experience
- Projects
- Certifications
- Achievements
- Languages

Each chunk stores metadata such as:

```text
chunk_id
section
title
page
content
````

This significantly improves retrieval precision.

---

# Semantic Retrieval

The retrieval pipeline uses:

* Sentence Transformers
* all-MiniLM-L6-v2
* FAISS Vector Search

Retrieval adapts dynamically based on query type.

### Project Queries

Retrieves only project-related chunks.

### Skills Queries

Retrieves Skills section.

### Education Queries

Retrieves Education section.

### Experience Queries

Retrieves Experience section.

### General Questions

Uses semantic similarity search.

---

# Local LLM Question Answering

Powered entirely by:

* Ollama
* Llama 3.2 (3B)

The assistant:

* Answers only using uploaded resume content.
* Avoids hallucinated information.
* Maintains session isolation.
* Supports follow-up questions.

---

# Architecture

```text
                 React Frontend
                        │
                        ▼
                 FastAPI Routes
                        │
                        ▼
                 Service Layer
                        │
                        ▼
                   CRUD Layer
                        │
                        ▼
                 SQLAlchemy ORM
                        │
                        ▼
                  PostgreSQL
                        │
                        ▼
            Resume Persistence Layer
                        │
                        ▼
             Ollama (Llama 3.2)
                        │
                        ▼
            Metadata Extraction Pipeline
```

---

# Resume Processing Workflow

```text
Resume Upload
      │
      ▼
Store Resume
      │
      ▼
Extract Text
      │
      ▼
Local LLM Metadata Extraction
      │
      ▼
Metadata Validation
      │
      ▼
Generate SHA256
      │
      ▼
Duplicate Detection
      │
      ▼
Store Resume in PostgreSQL
      │
      ▼
Store Resume as BYTEA
      │
      ▼
Generate metadata.csv
      │
      ▼
Return Resume UUID
```

---

# Technology Stack

## Frontend

* React
* Vite
* Axios

## Backend

* FastAPI
* Python 3.13

## Database

* PostgreSQL
* SQLAlchemy 2.0
* Pydantic v2

## Local AI

* Ollama
* Llama 3.2 (3B)

## Retrieval

* Sentence Transformers
* all-MiniLM-L6-v2
* FAISS

## Document Processing

* PyMuPDF
* pdfplumber
* pypdf
* EasyOCR

---

# Project Structure

```text
backend/
│
├── api/
├── models/
├── rag/
├── routes/
├── schemas/
├── services/
├── uploads/

database/
│
├── migrations/
├── connection.py
├── crud.py
├── models.py
├── init_db.py

frontend/
│
├── src/
├── package.json

.env
requirements.txt
README.md
```

---

# Installation

Clone the repository.

```bash
git clone <repository-url>
```

Create virtual environment.

```bash
python -m venv venv
```

Activate environment.

Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

Install backend dependencies.

```bash
pip install -r requirements.txt
```

Install frontend dependencies.

```bash
cd frontend
npm install
```

---

# PostgreSQL Setup

Create a PostgreSQL database.

```sql
CREATE DATABASE resume_platform;
```

Configure the `.env` file.

```env
DATABASE_URL=postgresql://postgres:<password>@localhost:5432/resume_platform
```

Initialize the database.

```bash
python database/init_db.py
```

---

# Ollama Setup

Verify installation.

```bash
ollama --version
```

Download the production model.

```bash
ollama pull llama3.2:3b
```

Start Ollama.

```bash
ollama serve
```

---

# Running the Application

Start backend.

```bash
uvicorn backend.main:app --reload
```

Backend:

```text
http://localhost:8000
```

Start frontend.

```bash
cd frontend
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Swagger:

```text
http://localhost:8000/docs
```

---

# API Endpoints

## Resume Management

| Method | Endpoint                 |
| ------ | ------------------------ |
| POST   | `/upload`                |
| GET    | `/resumes`               |
| GET    | `/resumes/{id}`          |
| PUT    | `/resumes/{id}`          |
| DELETE | `/resumes/{id}`          |
| GET    | `/resumes/{id}/download` |

---

# Local LLM Benchmark

The following Local LLMs were evaluated for metadata extraction.

| Model              | Overall Accuracy | Avg Inference Time |
| ------------------ | ---------------: | -----------------: |
| **Llama 3.2 (3B)** |       **96.55%** |        **35.54 s** |
| Mistral            |           96.55% |           108.04 s |
| Gemma 2B           |           93.10% |            32.56 s |
| Qwen 2.5 (3B)      |           89.66% |            35.29 s |

### Full Benchmark

| Metric                  | Result     |
| ----------------------- | ---------- |
| Candidate Name Accuracy | 91.74%     |
| Email Accuracy          | 96.19%     |
| Phone Accuracy          | 94.23%     |
| Overall Accuracy        | **94.03%** |

Llama 3.2 (3B) was selected as the production model due to its balance between metadata extraction accuracy, inference speed, hardware requirements, and seamless Ollama integration.

---

# Current Capabilities

* PDF Resume Processing
* DOCX Resume Processing
* Local LLM Metadata Extraction
* Resume-Aware Chunking
* Semantic Retrieval
* Recruiter CRUD Operations
* PostgreSQL Persistence
* Resume Download
* Duplicate Detection
* SHA256 Hashing
* Metadata Validation
* Resume Benchmarking
* React Recruiter Dashboard
* FastAPI REST APIs

---

# Future Roadmap

The next development phase will introduce recruiter-oriented natural language candidate search.

Planned architecture:

```text
Recruiter Query
        │
        ▼
Local LLM
        │
Generate SQL
        │
        ▼
PostgreSQL
        │
Matching Candidates
        │
        ▼
LLM Summary
```

Upcoming enhancements include:

* Natural Language SQL Search
* Semantic Candidate Search
* Advanced Recruiter Filters
* Candidate Ranking
* Job Description Matching
* Experience Extraction
* Recruiter Authentication
* Dashboard Analytics
* Cloud Deployment
* Audit History

---

# License

This project was developed as part of an internship project for educational and research purposes.

---

# Author

**Meghna Tomar**

AI | Machine Learning | NLP | FastAPI | React | PostgreSQL | Local LLMs

```
```
