# Changelog

All notable changes to the Legal Clause Analyzer project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## v1.0.0-beta — 2026-07-27

### Added

- **Knowledge Base** — 10 plain-text legal reference documents (GDPR Article 5, 13, 32, Data Protection Principles, EU AI Act High-Risk AI Systems, EU AI Act Human Oversight, Force Majeure, Confidentiality, Limitation of Liability, Termination) in `knowledge_base/`.
- **RAG references in PDF reports** — the generated PDF now includes a "Referenced Legal Sources" section showing document title, filename, and excerpt when RAG retrieval is active.

### Changed

- **Prompt engineering refactor** — split the LLM prompt into named constants (`SYSTEM_INSTRUCTIONS`, `ANALYSIS_INSTRUCTIONS`, `OUTPUT_FORMAT_INSTRUCTIONS`, `CONTRACT_TEXT_SECTION`) for maintainability.
- **Improved LLM report quality** — updated prompt structure to produce more concise, professional reports with sections: Executive Summary, Key Legal Findings, GDPR Assessment, EU AI Act Assessment, Overall Risk Evaluation, Practical Recommendations.
- **Upload size limits** — all file-upload endpoints now reject files larger than 10 MB with a 413 response.
- **Thread-safe global state** — added `threading.Lock` guards around shared `latest_analysis` and `latest_comparison` writes to prevent race conditions under concurrent requests.
- **Cross-platform temp directory** — replaced hardcoded Windows path with `tempfile.gettempdir()` for the comparison PDF download endpoint.

### Fixed

- `.dockerignore` now excludes `vector_store/` to prevent bloating the Docker image.

## v1.0.0-alpha — 2026-07-22

### Added

- **Rule-based legal clause detection** — keyword-driven detection of clause types including Force Majeure, Liability Limitation, Termination, Confidentiality, Data Protection, and AI Systems, each with an assigned risk level (High/Medium/Low) and explanation.
- **GDPR readiness analysis** — detection of personal-data and sensitive-data language, identification of missing GDPR controls (lawful basis, retention, security, data subject rights, processor/controller roles), issues, and recommendations.
- **EU AI Act readiness analysis** — detection of AI-system and high-risk AI terms, identification of missing AI Act controls (human oversight, transparency, logging, risk management, data governance, incident reporting), issues, and recommendations.
- **Risk scoring** — computed overall risk score (0–100) based on detected clause risk levels and missing compliance controls, with separate GDPR and EU AI Act readiness scores.
- **Contract comparison** — side-by-side comparison of two contracts showing added/removed/common clause types, score deltas with trends, and GDPR/EU AI Act comparison sections.
- **PDF report generation** — professional PDF reports for single-contract analysis and contract comparison using ReportLab, with color-coded scores, tables, and structured sections.
- **Local LLM support (Ollama)** — integration with locally running Ollama models (Llama 3) for optional AI-powered compliance summaries, keeping all contract data on-premise.
- **Local RAG pipeline** — full retrieval-augmented generation pipeline for grounding LLM summaries in a curated legal reference corpus.
- **ChromaDB indexing** — persistent vector store built from legal reference documents, with configurable chunking and embedding via the `rag/` module.
- **Retriever** — similarity-based retrieval from ChromaDB returning the most relevant chunks with metadata (filename, chunk index, distance).
- **Grounded LLM summaries** — LLM prompts are prepended with retrieved legal references so generated summaries are grounded in authoritative sources.
- **Referenced Legal Sources in PDF** — when LLM summarization is enabled, the PDF report includes a dedicated section listing every retrieved reference (filename and chunk index) used to ground the prompt.
- **Docker support** — `Dockerfile` and `docker-compose.yml` for containerized deployment with a single command.
- **GitHub Actions CI** — automated test suite execution on every push and pull request to `main` and `dev` branches.
- **Professional README** — comprehensive documentation covering features, architecture, setup, API reference, Docker usage, RAG pipeline, project structure, and contribution guidelines.
