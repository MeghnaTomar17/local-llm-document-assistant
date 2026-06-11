# Resume Intelligence Assistant

A local resume intelligence assistant powered by Ollama, Llama 3.2, FastAPI, React, sentence-transformers, and FAISS.

The app supports PDF and DOCX resumes, resume-aware chunking, semantic retrieval, session-based memory, quick actions, chat export, source attribution, response timing, and retrieval diagnostics.

## Key Features

* Upload PDF or DOCX resumes.
* Use layered PDF extraction for visual resumes: PyMuPDF block ordering, pdfplumber, pypdf, then OCR fallback when extraction quality is poor.
* Split resumes into logical sections: Contact Information, Summary, Education, Skills, Experience, Projects, Certifications, Achievements, and Languages.
* Store chunk metadata: `chunk_id`, `section`, `title`, `page`, and `content`.
* Keep each uploaded resume in its own runtime session with isolated chat history, metadata, chunks, and FAISS index.
* Regenerate `metadata.txt` and `metadata.csv` after each upload with metadata for all resumes uploaded in the current runtime session.
* Switch between resume sessions without cross-resume context leakage.
* Use Ollama and Llama 3.2 for local answers.

## Resume Retrieval

Retrieval is dynamic:

* Specific project questions retrieve only the matching project chunk.
* Section questions such as skills, education, experience, certifications, achievements, and languages retrieve the matching section chunk or chunks.
* Summary and overview questions retrieve multiple relevant resume sections.
* General questions fall back to FAISS semantic retrieval with a small context window.

The prompt instructs the model to use only resume information, avoid invented details, avoid mixing projects, and clearly state when information is unavailable.

## Debug Mode

Developer debug mode can be toggled in the UI to inspect extracted text, generated chunks, chunk metadata, retrieved chunks, similarity scores, and the final context sent to the LLM.
Debug output also shows the extraction method and quality signals used before metadata generation.
Set `PDF_EXTRACTION_DEBUG=1` before starting the backend or Streamlit app to print PyMuPDF block coordinates and detected single-column or multi-column layouts.

## APIs

* `POST /upload`
* `POST /ask`
* `GET /stats`
* `GET /chat-history`
* `POST /clear-chat`
* `GET /sessions`
* `GET /debug`
* `GET /metadata`
* `POST /switch-session`

## Install

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Install and run Ollama:

```bash
ollama pull llama3.2:3b
ollama serve
```

The first semantic indexing run downloads the `all-MiniLM-L6-v2` embedding model.

## Run FastAPI Backend

```bash
uvicorn backend.main:app --reload
```

Backend URL:

```text
http://localhost:8000
```

## Run React Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Run Streamlit App

```bash
streamlit run app.py
```

## Notes

* Runtime resume sessions are in memory. Re-upload resumes after restarting the backend process.
* Runtime metadata records are also in memory. Fresh app starts recreate empty `metadata.txt` and `metadata.csv`.
* Each resume session owns its own in-memory FAISS index.
* DOC files are no longer accepted; use PDF or DOCX resumes.
* EasyOCR is included for image-heavy PDF fallback. PaddleOCR is also supported if installed separately.
