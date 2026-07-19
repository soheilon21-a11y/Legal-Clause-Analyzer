# ⚖️ Legal Clause Analyzer
![Python](https://img.shields.io/badge/Python-3.12-blue)

![FastAPI](https://img.shields.io/badge/FastAPI-Framework-green)

![License](https://img.shields.io/badge/License-Educational-lightgrey)

![Status](https://img.shields.io/badge/Status-v1.2_Stable-success)

![LLM](https://img.shields.io/badge/LLM-Ollama%20%2B%20Llama%203-orange) 

A privacy-first AI-powered legal contract analyzer that detects legal clauses, evaluates GDPR and EU AI Act compliance, calculates risk scores, and generates professional compliance reports — all running locally.

## Highlights

- Privacy-first architecture
- Local LLM integration (Ollama + Llama 3)
- GDPR readiness assessment
- EU AI Act compliance assessment
- Professional PDF analysis and comparison reports
- FastAPI REST API 

---

# Overview

Legal Clause Analyzer is designed to help legal professionals, compliance teams, and AI developers quickly identify legal risks in contracts without sending confidential documents to external cloud services.

The project combines rule-based legal analysis with a locally running Large Language Model (Llama 3) to provide detailed compliance insights.

---

# Key Features

✅ Local PDF contract analysis

✅ Local DOCX contract analysis

✅ Compare two legal contracts side by side

✅ Automatic clause detection

- Force Majeure
- Liability Limitation
- Termination
- Confidentiality
- Data Protection
- AI Systems

✅ GDPR readiness assessment

✅ EU AI Act compliance assessment

✅ Legal risk scoring

✅ Professional PDF report generation

✅ Professional Contract Comparison PDF report

✅ Optional LLM-powered legal summary

✅ Privacy-first architecture

---

## API Documentation

The project exposes a REST API built with FastAPI.

### Swagger UI (v1.2)

![Swagger UI](images/swagger-v12.png)

---

## Sample Compliance Report

Below is an example of the automatically generated PDF compliance report.

![PDF Report](images/pdf-report.png) 

---

# Contract Comparison

Compare two legal contracts side by side and receive a structured compliance comparison report.

### Features

- Clause comparison
- Overall risk score comparison
- GDPR readiness comparison
- EU AI Act readiness comparison
- Professional PDF comparison report

### Comparison Endpoint

Upload two PDF or DOCX contracts for automated comparison.

![Compare Endpoint](images/compare-endpoint.png)

### JSON Response

Structured JSON response including clause analysis, compliance assessment and risk score comparison.

![Comparison JSON](images/comparison-json.png)

### Comparison PDF Report

Automatically generated professional comparison report.

![Comparison Report](images/comparison-report.png)

---

# Architecture

```
                PDF Contract
                      │
                      ▼
             PyMuPDF Text Extraction
                      │
                      ▼
         Rule-Based Clause Detection
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 GDPR Compliance Check      EU AI Act Check
        │                           │
        └─────────────┬─────────────┘
                      ▼
              Risk Score Engine
                      │
                      ▼
       Optional Local Llama 3 Analysis
                      │
                      ▼
      Professional Compliance PDF Report
```

---

# Technology Stack

- Python 3.12
- FastAPI
- ReportLab
- PyMuPDF
- Ollama
- Llama 3
- Pydantic
- Uvicorn

---

# Project Structure

```
Legal-Clause-Analyzer/
│
├── images/
│   ├── compare-endpoint.png
│   ├── comparison-json.png
│   ├── comparison-report.png
│   ├── pdf-report.png
│   ├── swagger-v12.png
│   └── swagger.png 
│
├── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Installation

Clone the repository

```bash
git clone https://github.com/soheilon21-a11y/Legal-Clause-Analyzer.git
```

Install dependencies

```bash
pip install -r requirements.txt
```

Start Ollama

```bash
ollama serve
```

Run FastAPI

```bash
uvicorn main:app --reload
```

---

# API Endpoints

## Analyze Contract

```
POST /analyze
```

Analyze plain text contracts.

---

## Analyze PDF

```
POST /analyze-pdf
```

Upload a PDF contract and receive:

- Clause detection
- GDPR analysis
- EU AI Act analysis
- Risk scores
- Professional PDF report

---

## Analyze DOCX

```
POST /analyze-docx
```

Upload a DOCX contract and receive:

- Clause detection
- GDPR analysis
- EU AI Act analysis
- Risk scores
- Professional PDF report

---

## Compare Contracts

```
POST /compare-contracts
```

Upload two PDF or DOCX contracts and receive:

- Side-by-side clause comparison
- Risk score comparison
- GDPR comparison
- EU AI Act comparison
- Comparison PDF report

--- 

## Download Comparison Report

```
GET /download-comparison-report
```

Download the latest generated comparison PDF report. 

--- 

# Example Workflow

```
Upload Contract
        │
        ▼
Extract Text
        │
        ▼
Detect Legal Clauses
        │
        ▼
GDPR Analysis
        │
        ▼
EU AI Act Analysis
        │
        ▼
Risk Scoring
        │
        ▼
Optional LLM Summary
        │
        ▼
Generate Professional PDF Report
```

---

# Example Output

The generated report includes:

- Executive Summary
- Risk Summary Table
- Detected Clauses
- GDPR Findings
- GDPR Recommendations
- EU AI Act Findings
- EU AI Act Recommendations
- Optional LLM Summary

---

# Privacy

This project follows a privacy-first approach.

All analysis can run locally using Ollama and Llama 3.

No contract text is sent to external cloud AI services.

---

# Current Development Status

Current Version:

**v1.2 Stable**

Implemented:

- PDF Upload
- DOCX Upload 
- Contract Comparison
- Local LLM Integration (Ollama + Llama 3) 
- Clause Detection
- GDPR Analysis
- EU AI Act Analysis
- Risk Scoring
- Professional PDF Report 
- Professional Contract Comparison PDF Report

Planned Features:

- Risk Dashboard
- Docker Support
- Unit Tests
- Retrieval-Augmented Generation (RAG)
- Prompt Engineering Improvements

---

# License 

This project is intended for educational and research purposes. 

The generated reports are compliance-readiness assessments and do not constitute legal advice.

---

# Author

Developed by Soheil

Legal Technology • AI Compliance • FastAPI • Local LLMs 

Repository: https://github.com/soheilon21-a11y/Legal-Clause-Analyzer 