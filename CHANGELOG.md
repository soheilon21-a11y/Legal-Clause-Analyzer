# Changelog

All notable changes to the Legal Clause Analyzer project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
