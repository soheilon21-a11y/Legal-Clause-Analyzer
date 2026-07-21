# Legal Clause Analyzer

![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green)
![License](https://img.shields.io/badge/License-Educational-lightgrey)
![Status](https://img.shields.io/badge/Status-Development)
![LLM](https://img.shields.io/badge/LLM-Ollama%20%2B%20Llama%203-orange)
![RAG](https://img.shields.io/badge/RAG-ChromaDB%20%2B%20bge--small-purple)

A privacy-first, AI-powered legal contract analyzer that detects legal clauses, evaluates GDPR and EU AI Act readiness, calculates risk scores, grounds LLM summaries in a local knowledge base via RAG, and generates professional compliance reports — all running locally.

---

## 1. Project Overview

Legal Clause Analyzer helps legal professionals, compliance teams, and AI developers quickly identify legal risks in contracts **without sending confidential documents to external cloud services**.

The project combines deterministic, rule-based legal analysis with a locally running Large Language Model (Llama 3 via Ollama) and a local Retrieval-Augmented Generation (RAG) pipeline that grounds LLM summaries in reference legal clauses stored on your own machine.

---

## 2. Key Features

- PDF, DOCX, and plain-text contract analysis
- Automatic clause detection — Force Majeure, Liability Limitation, Termination, Confidentiality, Data Protection, AI Systems
- GDPR readiness assessment
- EU AI Act compliance assessment
- Legal risk scoring (overall, GDPR readiness, EU AI Act readiness)
- Side-by-side contract comparison with structured JSON diff
- Professional PDF analysis and comparison reports
- Optional LLM-powered compliance summaries (local, via Ollama)
- Local RAG pipeline — LLM summaries grounded in retrieved legal references
- Offline index builder for the knowledge base
- Docker support and GitHub Actions CI
- Privacy-first architecture — no external cloud calls

---

## 3. Architecture Overview

```
              PDF / DOCX / Text
                      │
                      ▼
        PyMuPDF / python-docx Extraction
                      │
                      ▼
         Rule-Based Clause Detection
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 GDPR Readiness Check      EU AI Act Check
        │                           │
        └─────────────┬─────────────┘
                      ▼
              Risk Score Engine
                      │
                      ▼
      Optional Local LLM Summary ◄── RAG Retriever (Top-3 references)
                      │
                      ▼
       Professional Compliance PDF Report
```

---

## 4. Project Structure

```
Legal-Clause-Analyzer/
│
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions CI (pytest)
│
├── images/                         # README screenshots
│   ├── compare-endpoint.png
│   ├── comparison-json.png
│   ├── comparison-report.png
│   ├── pdf-report.png
│   ├── swagger-v12.png
│   └── swagger.png
│
├── knowledge_base/                 # .txt reference documents for RAG
│   └── .gitkeep
│
├── rag/                            # RAG pipeline package
│   ├── __init__.py
│   ├── config.py                   # Paths, collection name, chunk settings
│   ├── document_loader.py          # Loads .txt files from knowledge_base/
│   ├── text_chunker.py             # Overlapping character-based chunking
│   ├── embeddings.py               # sentence-transformers wrapper (lazy-loaded)
│   ├── index_builder.py            # Offline ChromaDB index builder
│   ├── retriever.py                # Top-K similarity retrieval
│   └── vector_store.py             # Reserved placeholder module
│
├── tests/                          # pytest suite (FastAPI TestClient)
│   ├── sample_files/               # Future PDF/DOCX fixtures
│   │   └── .gitkeep
│   ├── __init__.py
│   ├── conftest.py                 # Shared fixtures (client, texts, factories)
│   ├── test_analyze.py
│   ├── test_compare.py
│   └── test_health.py
│
├── main.py                         # FastAPI application (single module)
├── requirements.txt                # Runtime dependencies
├── requirements-dev.txt            # Test dependencies
├── pytest.ini
├── Dockerfile
├── .dockerignore
├── .gitignore
└── README.md
```

---

## 5. Installation

Clone the repository:

```bash
git clone https://github.com/soheilon21-a11y/Legal-Clause-Analyzer.git
cd Legal-Clause-Analyzer
```

Install runtime dependencies:

```bash
pip install -r requirements.txt
```

For development (testing), also install:

```bash
pip install -r requirements-dev.txt
```

---

## 6. Running the API

Start Ollama (optional — only needed for LLM summaries):

```bash
ollama serve
```

Start the API:

```bash
uvicorn main:app --reload
```

Interactive documentation is available at `http://127.0.0.1:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service status and info |
| `POST` | `/analyze` | Analyze plain-text contracts (JSON body) |
| `POST` | `/analyze-pdf` | Analyze an uploaded PDF contract |
| `POST` | `/analyze-docx` | Analyze an uploaded DOCX contract |
| `POST` | `/compare-contracts` | Compare two PDF/DOCX contracts |
| `GET` | `/download-report` | PDF report of the latest analysis |
| `GET` | `/download-comparison-report` | PDF report of the latest comparison |

All analysis endpoints accept `use_llm` (default `false`). When enabled, the response includes an LLM-generated compliance summary, augmented with retrieved legal references when a knowledge-base index exists.

Run the test suite:

```bash
pytest -v
```

---

## 7. Docker

Build the image:

```bash
docker build -t legal-clause-analyzer:1.3 .
```

Run the container:

```bash
docker run -d --name legal-clause-analyzer -p 8000:8000 legal-clause-analyzer:1.3
```

The API will be available at `http://localhost:8000/docs`.

Notes:

- The image runs uvicorn as a non-root user and includes a health check on `GET /`.
- Rule-based analysis works fully offline inside the container.
- Requests with `use_llm=True` require Ollama to be reachable from inside the container; otherwise the API gracefully returns its standard fallback summary.

---

## 8. GitHub Actions (CI)

The workflow at `.github/workflows/ci.yml` runs on **every push and pull request**:

1. Checks out the repository
2. Sets up Python 3.12 (with pip caching)
3. Installs `requirements.txt` and `requirements-dev.txt`
4. Runs the full test suite with `pytest -v`

The job uses least-privilege token permissions and a 10-minute timeout.

---

## 9. Local LLM Support

- **Engine:** [Ollama](https://ollama.com) running `llama3` at `http://127.0.0.1:11434/v1`
- LLM summaries are **opt-in** per request via `use_llm=True`.
- If Ollama is unreachable, the API returns a clear fallback message instead of failing the request — all rule-based analysis is unaffected.
- No contract text ever leaves the local machine.

---

## 10. RAG Architecture

The project includes a fully local Retrieval-Augmented Generation pipeline:

```
Documents
    ↓
Chunking
    ↓
Embeddings (BAAI/bge-small-en-v1.5)
    ↓
ChromaDB
    ↓
Retriever
    ↓
LLM
    ↓
Legal Report
```

**Pipeline components (`rag/` package):**

| Module | Responsibility |
|---|---|
| `document_loader.py` | Loads every non-empty `.txt` file from `knowledge_base/` |
| `text_chunker.py` | Splits documents into overlapping chunks (1000 chars, 200 overlap) |
| `embeddings.py` | Generates embeddings with `BAAI/bge-small-en-v1.5` (lazy-loaded) |
| `index_builder.py` | Offline builder — stores chunks + metadata in ChromaDB |
| `retriever.py` | Top-K similarity search over the local index |

**LLM integration (current):** when `use_llm=True`, the retriever fetches the Top-3 most relevant legal chunks and prepends them to the LLM prompt as reference context. If retrieval fails for any reason — missing index, empty collection, model error — the API silently falls back to the original prompt and never fails the request. The `use_llm=False` path is completely unaffected.

Build or refresh the index after changing the knowledge base:

```bash
python -m rag.index_builder
```

---

## 11. Knowledge Base

- **Location:** `knowledge_base/`
- **Format:** plain-text (`.txt`) reference documents — e.g., standard clause libraries, playbooks, or internal legal guidance.
- Empty files are ignored; files are loaded in deterministic filename order.
- After adding or editing documents, rebuild the index with `python -m rag.index_builder`.

---

## 12. Vector Store

- **Engine:** ChromaDB (local, persistent)
- **Location:** `vector_store/` (created on first indexing run; not committed to git)
- **Collection:** `legal_clauses`
- Each chunk is stored with its text, embedding, and metadata (`filename`, `chunk_index`) under a deterministic ID (`filename:chunk_index`), so re-running the index builder is idempotent and never creates duplicates.

---

## 13. Embedding Model

- **Model:** [`BAAI/bge-small-en-v1.5`](https://huggingface.co/BAAI/bge-small-en-v1.5)
- **Framework:** sentence-transformers (runs locally, 384-dimensional embeddings)
- The model is downloaded once from Hugging Face (~130 MB) on first use and cached locally; afterwards it runs fully offline.
- Loaded lazily — it is only initialized when indexing or retrieval actually runs.

---

## 14. Current Capabilities

- Full REST API for analysis, comparison, and PDF reporting
- Deterministic rule-based legal analysis (no external services required)
- Local LLM summaries with graceful offline fallback
- Offline RAG indexing and Top-3 retrieval, integrated into the LLM path
- Docker image with health check and non-root execution
- CI pipeline running a 19-test pytest suite on every push and pull request

---

## 15. Roadmap

- RAG references in generated PDF reports
- Expanded curated legal knowledge base
- Risk dashboard
- Split Docker images (slim API image vs. full RAG image)
- Prompt engineering improvements
- Additional file formats and batch analysis

---

## 16. License

This project is intended for **educational and research purposes**.

The generated reports are compliance-readiness assessments and **do not constitute legal advice**.

---

## Author

Developed by **Soheil**

Legal Technology • AI Compliance • FastAPI • Local LLMs • RAG

Repository: https://github.com/soheilon21-a11y/Legal-Clause-Analyzer
