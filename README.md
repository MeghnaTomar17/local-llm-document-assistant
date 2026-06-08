# Local LLM Document Assistant

A Python-based document intelligence assistant powered by a locally hosted LLM using Ollama and Llama 3.2.

The application allows users to upload PDF documents, ask questions about their content, generate summaries, extract key information, and perform document analysis entirely on their local machine without relying on cloud-based AI services.

---

## Features

### Local LLM Integration

* Ollama-based local deployment
* Llama 3.2 model execution
* Offline document analysis

### PDF Processing

* Dynamic PDF loading
* Text extraction using PyPDF
* Multi-page document support

### Document Intelligence

* Document summarization
* Question answering
* Architecture analysis
* Feature extraction
* Technology stack identification
* Use case analysis
* Future scope extraction
* Keyword extraction

### Retrieval System

* Document chunking
* Keyword-based retrieval
* Context selection
* Reduced prompt size

### Performance Monitoring

* Response generation timing
* Page count tracking
* Character count tracking
* Chunk statistics

---

## Project Workflow

PDF Document
↓
PyPDF Extraction
↓
Text Processing
↓
Chunk Generation
↓
Keyword-Based Retrieval
↓
Context Selection
↓
Ollama API
↓
Llama 3.2
↓
Response Generation

---

## Commands

| Command      | Description                  |
| ------------ | ---------------------------- |
| summary      | Generate document summary    |
| overview     | Generate high-level overview |
| purpose      | Identify document objective  |
| features     | Extract key features         |
| architecture | Explain architecture         |
| techstack    | Extract technologies used    |
| usecases     | Extract business use cases   |
| benefits     | Identify advantages          |
| future       | Future enhancements          |
| keywords     | Important keywords           |
| stats        | Display document statistics  |
| chunks       | Display chunk information    |
| help         | Show commands                |
| exit         | Exit application             |

Users can also ask custom natural-language questions.

---

## Installation

### Clone Repository

```bash
git clone <repository-url>
cd LocalLLM-Document-Assistant
```

### Create Virtual Environment

```bash
python -m venv venv
```

### Activate Environment

Windows:

```bash
.\venv\Scripts\Activate.ps1
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Install Ollama

Download and install Ollama.

Verify installation:

```bash
ollama --version
```

Pull the model:

```bash
ollama run llama3.2:3b
```

---

## Run Application

```bash
python pdf_reader.py
```

Provide the PDF path when prompted.

Example:

```text
Enter PDF path:
C:\Users\Meghna Tomar\Downloads\Ghostworker.pdf
```

---

## Sample Output

```text
Pages: 11
Characters Extracted: 4861
Chunks Created: 5

Ask a question:
features
```

Output:

```text
Multi-agent AI workforce
OCR extraction
Validation engine
Browser automation
Workflow dashboard
Automated communication
```

---

## Technologies Used

* Python
* Ollama
* Llama 3.2
* PyPDF
* Requests

---