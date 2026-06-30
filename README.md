# Resume Intelligence Platform

> A fully local, AI-powered Resume Intelligence Platform built using **FastAPI**, **React**, **PostgreSQL**, **Ollama**, **Llama 3.2**, **FAISS**, and **Sentence Transformers**.

The **Resume Intelligence Platform** is an AI-powered application designed to automate resume processing, intelligent metadata extraction, persistent storage, recruiter management, and semantic retrieval while ensuring complete data privacy through locally hosted Large Language Models (LLMs).

Unlike traditional cloud-based resume parsing systems, every stage of processing—including document extraction, metadata generation, semantic retrieval, and question answering—is performed locally using Ollama. This ensures that sensitive candidate information never leaves the organization's infrastructure.

The platform combines deterministic validation techniques with Local LLM reasoning to produce accurate and reliable candidate metadata, while PostgreSQL provides persistent storage for both extracted information and uploaded resume files.

---

# Features

##  Resume Upload & Processing

The platform supports intelligent processing of multiple resume formats and layouts.

### Supported File Formats

- PDF (`.pdf`)
- Microsoft Word (`.docx`)

### Supported Resume Types

- ATS-friendly resumes
- Canva resumes
- Designer resumes
- Multi-column resumes
- Academic resumes
- Professional resumes

### Document Processing Pipeline

Each uploaded resume passes through a multi-stage extraction pipeline consisting of:

- PyMuPDF block extraction
- pdfplumber extraction
- pypdf extraction
- EasyOCR fallback for scanned documents
- Extraction quality assessment
- Resume-aware section detection
- Resume-aware chunking

To prevent duplicate records, every uploaded document is assigned a unique **SHA256 hash**, which is used for duplicate detection before storing the resume.

---

# AI Metadata Extraction

The Resume Intelligence Platform combines **Local LLM reasoning** with **deterministic validation** to generate structured candidate metadata.

The current implementation extracts the following information from every uploaded resume:

- Candidate Name
- Email Address
- Phone Number
- Technical Skills
- Cities / Locations
- Fresher Status

The extracted information is validated before being stored permanently in PostgreSQL.

## Metadata Validation Pipeline

To improve extraction accuracy, every metadata field passes through dedicated validation rules.

### Candidate Name Validation

- Section heading rejection
- Organization filtering
- Email username contamination prevention
- Uppercase normalization
- Initial handling
- Multi-word name support

### Email Validation

- Pattern validation
- Invalid email rejection
- Automatic fallback extraction

### Phone Number Validation

- Country code handling
- Leading zero preservation
- Invalid number filtering
- Date and year rejection
- International number support

This hybrid extraction approach combines the flexibility of Large Language Models with the reliability of deterministic validation.

---

# Resume Persistence

Unlike earlier prototype versions, the Resume Intelligence Platform now stores all candidate information permanently in PostgreSQL.

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

Uploaded resumes are stored in two locations:

- Local Disk
- PostgreSQL (BYTEA)

PostgreSQL serves as the **single source of truth**, while generated metadata files are retained only for debugging and development purposes.

---

# Recruiter Management

The platform provides recruiter-oriented resume management capabilities through a REST-based API.

Supported operations include:

- View all resumes
- View individual resume details
- Edit extracted metadata
- Download stored resumes
- Delete candidate records

Recruiters can update the following fields:

- Candidate Name
- Email Address
- Phone Number
- Technical Skills
- Cities
- Fresher Status
- Recruiter Notes

Once recruiter verification is complete, the system automatically marks the candidate record as verified and updates the modification timestamp.

---

# Resume-Aware Chunking

Instead of splitting resumes into fixed-size text chunks, the Resume Intelligence Platform implements **resume-aware chunking**, where resumes are divided into meaningful logical sections.

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

Each generated chunk stores the following metadata:

```text
chunk_id
section
title
page
content
```

This structured representation enables the retrieval engine to identify only the most relevant portions of a resume, improving semantic retrieval accuracy while minimizing unnecessary context provided to the Local LLM.

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

---

# Bulk Resume Processing

The project includes a command-line utility for processing large collections of resumes without using the React frontend or FastAPI Swagger interface.

This utility is intended for recruiter evaluation, large-scale testing, and benchmarking scenarios involving hundreds or thousands of resumes.

## Features

- Process an entire folder of resumes recursively.
- Supports both **PDF** and **DOCX** formats.
- Automatically extracts metadata using the existing Resume Intelligence pipeline.
- Stores processed resumes in PostgreSQL.
- Preserves duplicate detection through SHA256 hashing.
- Displays processing progress using a terminal progress bar.
- Generates detailed processing logs.
- Exports a CSV processing report summarizing the results.

## Usage

Run the utility from the project root.

```bash
python bulk_process.py "<folder_path>"
```

Example:

```bash
python bulk_process.py "D:\Resume_Dataset"
```

The script scans the specified directory recursively and processes every supported resume found.

## Generated Outputs

After execution, the following files are generated:

| File | Description |
|------|-------------|
| `processing_report.csv` | Summary of processed resumes, processing time, status, and Resume UUID |
| `bulk_processing.log` | Detailed processing logs and error information |

## Typical Workflow

```text
Resume Folder
        │
        ▼
Recursive File Discovery
        │
        ▼
Resume Processing Pipeline
        │
        ▼
Metadata Extraction
        │
        ▼
Duplicate Detection
        │
        ▼
PostgreSQL Storage
        │
        ▼
CSV Report + Log File
```

The utility is designed for large-scale evaluation and can be used to process hundreds or thousands of resumes using the same extraction pipeline as the web application.

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
