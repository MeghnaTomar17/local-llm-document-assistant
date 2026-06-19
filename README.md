# Resume Intelligence Assistant

A local AI-powered Resume Intelligence Assistant built using **Ollama**, **Llama 3.2**, **FastAPI**, **React**, **Sentence Transformers**, and **FAISS**.

The system supports advanced resume processing, metadata extraction, semantic retrieval, resume-aware chunking, session management, benchmarking, and local LLM-powered question answering without relying on external APIs.

---

# Features

## Resume Upload & Processing

* Upload PDF and DOCX resumes.
* Support for ATS-friendly resumes, Canva resumes, designer resumes, and multi-column layouts.
* Layered PDF extraction pipeline:

  * PyMuPDF block extraction
  * pdfplumber extraction
  * pypdf extraction
  * OCR fallback (EasyOCR)
* Automatic extraction quality assessment.
* Resume-aware chunking based on logical sections.

---

## Resume Metadata Extraction

Hybrid metadata extraction pipeline combining:

1. LLM-first extraction using Ollama.
2. Metadata validation layer.
3. Deterministic fallback extraction.

### Extracted Fields

* Candidate Name
* Email Address
* Phone Number
* Alternate Phone Numbers

### Metadata Validation

#### Candidate Name Validation

* Section heading rejection.
* Email username contamination prevention.
* Initial and multi-word name support.
* Uppercase name normalization.
* Invalid pattern filtering.

#### Email Validation

* Pattern validation.
* Malformed email rejection.
* Automatic fallback support.

#### Phone Validation

* Country code handling.
* Date and year filtering.
* Invalid number rejection.
* Alternate phone support.
* Normalized benchmark comparison.

---

## Resume-Aware Chunking

Resumes are split into logical sections:

* Contact Information
* Summary
* Education
* Skills
* Experience
* Projects
* Certifications
* Achievements
* Languages

Each chunk stores metadata including:

```text
chunk_id
section
title
page
content
```

---

## Semantic Retrieval

Uses:

* Sentence Transformers (`all-MiniLM-L6-v2`)
* FAISS Vector Search

Retrieval behavior is dynamic:

### Project Questions

Retrieves only project-related chunks.

### Section Questions

Retrieves targeted chunks from:

* Skills
* Education
* Experience
* Certifications
* Achievements
* Languages

### Resume Overview Questions

Retrieves multiple sections for broader context.

### General Questions

Falls back to semantic similarity retrieval.

---

## Session Management

Each uploaded resume operates in an isolated runtime session.

### Session Isolation

Every session maintains:

* Chat history
* Metadata
* Resume chunks
* FAISS index
* Retrieval context

This prevents cross-resume information leakage.

### Session Switching

Users can:

* View all uploaded resume sessions.
* Switch between sessions.
* Continue conversations independently.

---

## Metadata Storage

After each upload:

* metadata.txt is regenerated.
* metadata.csv is regenerated.

Files contain validated metadata records for all resumes uploaded during the current runtime session.

---

## Local LLM Question Answering

Powered by:

* Ollama
* Llama 3.2

Prompting strategy ensures:

* Answers use only resume information.
* No hallucinated details.
* No project mixing.
* Missing information is explicitly acknowledged.

---

# Metadata Benchmarking Framework

A dedicated benchmarking system evaluates extraction accuracy against manually verified ground-truth datasets.

## Benchmark Metrics

* Candidate Name Accuracy
* Email Accuracy
* Phone Number Accuracy
* Overall Metadata Accuracy
* Average Inference Time
* Failure Analysis

## Run Benchmark

```bash
python benchmark_llm_metadata.py training_data/resumes --model llama
```

Example Output:

```text
candidate_name: 92.00%
email: 100.00%
phone_number: 100.00%

OVERALL: 97.00%
```

---

# Extraction Quality Analysis

Every uploaded resume generates extraction diagnostics.

### Quality Signals

* Character Count
* Readable Word Ratio
* Email Detection
* Phone Detection
* Resume Section Detection
* Scrambled Text Score
* Poor Extraction Detection

This information is used to determine whether OCR fallback is required.

---

# Debug Mode

Developer debug mode can be enabled from the UI.

### Debug Information

* Extracted text
* Resume chunks
* Chunk metadata
* Similarity scores
* Retrieved chunks
* Final retrieval context
* Extraction method
* Extraction quality diagnostics

Enable extraction debugging:

```powershell
$env:PDF_EXTRACTION_DEBUG="1"
```

This prints:

* PyMuPDF block coordinates
* Layout analysis
* Single-column detection
* Multi-column detection

---

# Supported Metadata Models

Configure metadata extraction model:

```powershell
$env:OLLAMA_METADATA_MODEL="llama3.2:3b"
```

Supported aliases:

```text
llama
llama3.2
llama3.2:3b
qwen
mistral
gemma
```

Custom Ollama model tags are also supported.

---

# Timeout Configuration

Configure metadata extraction timeout:

```powershell
$env:OLLAMA_METADATA_TIMEOUT_SECONDS="300"
```

The system automatically falls back to deterministic extraction if the LLM times out.

---

# API Endpoints

## Resume Management

```http
POST /upload
GET /sessions
POST /switch-session
```

## Chat

```http
POST /ask
GET /chat-history
POST /clear-chat
```

## Metadata

```http
GET /metadata
```

## Diagnostics

```http
GET /stats
GET /debug
```

---

# Installation

Create virtual environment:

```bash
python -m venv venv
```

Activate:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# Ollama Setup

Install and pull model:

```bash
ollama pull llama3.2:3b
```

Start Ollama:

```bash
ollama serve
```

---

# Backend

Run FastAPI backend:

```bash
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

---

# Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

---

# Streamlit Version

```bash
streamlit run app.py
```

---

# Tech Stack

### Backend

* FastAPI
* Python

### Frontend

* React
* Vite

### LLM

* Ollama
* Llama 3.2

### Retrieval

* Sentence Transformers
* FAISS

### Document Processing

* PyMuPDF
* pdfplumber
* pypdf
* EasyOCR

### Data Handling

* CSV
* Runtime Metadata Store

---

# Current Limitations

* Runtime sessions are stored in memory.
* Metadata is not persisted across backend restarts.
* Resumes must be re-uploaded after restart.
* FAISS indices are session-local and recreated after restart.
* DOC files are not supported.
* OCR processing may increase extraction time for image-heavy resumes.

---

# Future Enhancements

* City / Location Extraction
* Consolidated Metadata Storage
* Persistent Session Storage
* Multi-Candidate Resume Handling
* Enhanced Metadata Dashboard
* Advanced Resume Analytics
* Recruiter-Oriented Search & Filtering

---

# Project Goal

Build a fully local, privacy-preserving Resume Intelligence Assistant capable of:

* Resume understanding
* Metadata extraction
* Semantic search
* Context-aware question answering
* Retrieval diagnostics
* Resume benchmarking

without relying on external cloud LLM APIs.
