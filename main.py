from typing import Any
import fitz             
from docx import Document

from fastapi import FastAPI, UploadFile, File, HTTPException                
from openai import OpenAI
from pydantic import BaseModel, Field
from reportlab.platypus import SimpleDocTemplate, Paragraph 
from reportlab.platypus import Table, TableStyle 
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch 
from fastapi.responses import StreamingResponse 
from io import BytesIO  


LOCAL_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
MODEL_ID = "llama3"

client = OpenAI(
    base_url=LOCAL_LLM_BASE_URL,
    api_key="ollama",
)

app = FastAPI(
    title="Legal Clause Analyzer",
    version="0.1.0",
    description=(
        "Privacy-first legal clause analyzer with local LLM support."
    ),
)
latest_analysis = {}


class AnalyzeRequest(BaseModel):
    contract_text: str = Field(
        ...,
        min_length=20,
        description="Contract text to analyze.",
    )
    use_llm: bool = Field(
        default=False,
        description="Use local Ollama LLM for a short summary.",
    )


CLAUSE_RULES: list[dict[str, Any]] = [
    {
        "name": "Force Majeure",
        "keywords": [
            "force majeure",
            "act of god",
            "unforeseeable event",
            "natural disaster",
        ],
        "risk_level": "Medium",
        "explanation": (
            "Review notice duties, suspension rights, and termination rights."
        ),
    },
    {
        "name": "Liability Limitation",
        "keywords": [
            "liability",
            "limit liability",
            "limitation of liability",
            "cap on liability",
        ],
        "risk_level": "High",
        "explanation": (
            "Liability may be limited. Check whether remedies are one-sided."
        ),
    },
    {
        "name": "Termination",
        "keywords": [
            "termination",
            "terminate this agreement",
            "termination for convenience",
            "termination for cause",
        ],
        "risk_level": "Medium",
        "explanation": (
            "Check notice periods, cure periods, and post-termination duties."
        ),
    },
    {
        "name": "Confidentiality",
        "keywords": [
            "confidential information",
            "confidentiality",
            "non-disclosure",
            "trade secret",
        ],
        "risk_level": "Medium",
        "explanation": (
            "Check scope, duration, exceptions, and return or deletion duties."
        ),
    },
    {
        "name": "Data Protection",
        "keywords": [
            "personal data",
            "data protection",
            "gdpr",
            "data subject",
            "processor",
            "controller",
        ],
        "risk_level": "High",
        "explanation": (
            "Personal data may be involved. Check GDPR roles and safeguards."
        ),
    },
    {
        "name": "AI Systems",
        "keywords": [
            "ai system",
            "artificial intelligence",
            "machine learning",
            "automated decision",
            "automated decision-making",
            "algorithmic decision",
        ],
        "risk_level": "High",
        "explanation": (
            "AI usage detected. Review EU AI Act and data governance duties."
        ),
    },
]

AI_SYSTEM_KEYWORDS: list[str] = [
    "ai system",
    "artificial intelligence",
    "machine learning",
    "automated decision",
    "automated decision-making",
    "algorithmic decision",
    "predictive model",
]

HIGH_RISK_AI_KEYWORDS: list[str] = [
    "employment",
    "worker management",
    "credit scoring",
    "education",
    "biometric identification",
    "law enforcement",
    "migration",
    "essential private services",
    "essential public services",
]

PERSONAL_DATA_KEYWORDS: list[str] = [
    "personal data",
    "personally identifiable information",
    "pii",
    "data subject",
    "customer data",
    "employee data",
    "user data",
]

SENSITIVE_DATA_KEYWORDS: list[str] = [
    "health data",
    "biometric data",
    "genetic data",
    "racial or ethnic origin",
    "political opinions",
    "religious beliefs",
    "trade union",
    "sexual orientation",
]

AI_ACT_CONTROL_CHECKS: dict[str, list[str]] = {
    "human oversight": [
        "human oversight",
        "human review",
        "manual review",
        "human-in-the-loop",
    ],
    "transparency": [
        "transparency",
        "user notice",
        "disclosure",
        "explainability",
    ],
    "logging": [
        "logging",
        "logs",
        "audit trail",
        "record keeping",
    ],
    "risk management": [
        "risk management",
        "risk assessment",
        "mitigation measures",
    ],
    "data governance": [
        "data governance",
        "training data",
        "data quality",
        "dataset",
    ],
    "incident reporting": [
        "incident reporting",
        "serious incident",
        "notification duty",
    ],
}

GDPR_CONTROL_CHECKS: dict[str, list[str]] = {
    "lawful basis": [
        "lawful basis",
        "consent",
        "legitimate interest",
        "contractual necessity",
    ],
    "retention": [
        "retention",
        "deletion",
        "erase",
        "storage period",
    ],
    "security": [
        "encryption",
        "access control",
        "security measures",
        "confidentiality",
    ],
    "data subject rights": [
        "data subject rights",
        "access request",
        "rectification",
        "erasure",
        "objection",
    ],
    "processor/controller roles": [
        "controller",
        "processor",
        "data processing agreement",
        "dpa",
    ],
}


def match_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def find_missing_controls(
    lower_text: str,
    controls: dict[str, list[str]],
) -> list[str]:
    missing: list[str] = []

    for control_name, keywords in controls.items():
        if not has_any(lower_text, keywords):
            missing.append(control_name)

    return missing


def detect_clauses(text: str) -> list[dict[str, Any]]:
    lower_text = text.lower()
    findings: list[dict[str, Any]] = []

    for rule in CLAUSE_RULES:
        matched = match_keywords(lower_text, rule["keywords"])

        if matched:
            findings.append(
                {
                    "clause_type": rule["name"],
                    "risk_level": rule["risk_level"],
                    "matched_keywords": matched,
                    "explanation": rule["explanation"],
                }
            )

    return findings


def ai_act_compliance_check(text: str) -> dict[str, Any]:
    lower_text = text.lower()

    ai_terms = match_keywords(lower_text, AI_SYSTEM_KEYWORDS)
    high_risk_terms = match_keywords(lower_text, HIGH_RISK_AI_KEYWORDS)
    missing_controls = find_missing_controls(
        lower_text,
        AI_ACT_CONTROL_CHECKS,
    )

    ai_act_triggered = bool(ai_terms)
    issues: list[str] = []
    recommendations: list[str] = []

    if ai_act_triggered:
        summary = (
            "AI-related language was detected. This is a readiness check, "
            "not a final legal compliance determination."
        )

        if high_risk_terms:
            issues.append(
                "Possible high-risk AI context detected. "
                "Human legal review is recommended."
            )

        if missing_controls:
            issues.append(
                "The contract may not clearly address: "
                + ", ".join(missing_controls)
                + "."
            )

        recommendations.extend(
            [
                "Clarify provider and deployer responsibilities.",
                "Add human oversight language where relevant.",
                "Document logging and audit-trail obligations.",
                "Review data governance and training-data clauses.",
                "Add transparency and user-notice obligations if needed.",
            ]
        )
    else:
        summary = (
            "No obvious AI-system language was detected. "
            "AI Act obligations are not clearly triggered by this text."
        )
        recommendations.append(
            "Keep this as a compliance-readiness check, not legal advice."
        )

    if not issues:
        issues.append(
            "No obvious AI Act issue was detected at keyword level."
        )

    return {
        "ai_act_triggered": ai_act_triggered,
        "matched_ai_terms": ai_terms,
        "matched_high_risk_terms": high_risk_terms,
        "missing_controls": missing_controls if ai_act_triggered else [],
        "issues": issues,
        "recommendations": recommendations,
        "summary": summary,
    }


def gdpr_privacy_check(text: str) -> dict[str, Any]:
    lower_text = text.lower()

    personal_data_terms = match_keywords(
        lower_text,
        PERSONAL_DATA_KEYWORDS,
    )
    sensitive_data_terms = match_keywords(
        lower_text,
        SENSITIVE_DATA_KEYWORDS,
    )
    missing_controls = find_missing_controls(
        lower_text,
        GDPR_CONTROL_CHECKS,
    )

    personal_data_detected = bool(personal_data_terms)
    sensitive_data_detected = bool(sensitive_data_terms)

    issues: list[str] = []
    recommendations: list[str] = []

    if personal_data_detected:
        issues.append(
            "Personal data language detected. GDPR safeguards should be "
            "reviewed."
        )

        if missing_controls:
            issues.append(
                "The contract may not clearly address: "
                + ", ".join(missing_controls)
                + "."
            )

        recommendations.extend(
            [
                "Clarify controller and processor roles.",
                "Add retention and deletion obligations.",
                "Include access control and encryption language.",
                "Address data subject rights where relevant.",
                "Avoid using real personal data in public demos.",
            ]
        )
    else:
        recommendations.append(
            "No obvious personal-data language detected at keyword level."
        )

    if sensitive_data_detected:
        issues.append(
            "Sensitive personal data may be involved. "
            "Apply stricter review and minimization controls."
        )

    if not issues:
        issues.append(
            "No obvious GDPR issue was detected at keyword level."
        )

    return {
        "personal_data_detected": personal_data_detected,
        "sensitive_data_detected": sensitive_data_detected,
        "matched_personal_data_terms": personal_data_terms,
        "matched_sensitive_data_terms": sensitive_data_terms,
        "missing_controls": missing_controls if personal_data_detected else [],
        "issues": issues,
        "recommendations": recommendations,
    }


def generate_llm_summary(
    text: str,
    findings: list[dict[str, Any]],
    ai_act_check: dict[str, Any],
    gdpr_check: dict[str, Any],
) -> str:
    prompt = f"""
You are an AI LegalTech Assistant specialized in:

- GDPR compliance
- EU AI Act compliance
- AI Governance
- Commercial contract review

This is NOT legal advice.

Based ONLY on the supplied analysis, generate a professional compliance report.

Use EXACTLY the following structure:

# Executive Summary

# Overall Risk Level

# GDPR Readiness

# EU AI Act Readiness

# Key Legal Risks

# Missing Compliance Controls

# Priority Recommendations
(List only the five most important recommendations.)

# Conclusion

# Disclaimer
State clearly that this is a compliance-readiness assessment and not legal advice.

Do not repeat the contract.

Do not invent facts.

Use only the supplied findings.

-------------------------

Clause Findings

{findings}

-------------------------

EU AI Act Analysis

{ai_act_check}

-------------------------

GDPR Analysis

{gdpr_check}

-------------------------

Contract Excerpt

{text[:6000]}
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cautious legal technology assistant. "
                        "You explain risks clearly and avoid legal advice."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.1,
            top_p=0.9,
            max_tokens=700,
        )

        content = completion.choices[0].message.content
        return content or "Local LLM returned an empty response."

    except Exception as exc:
        return (
            "Local LLM summary unavailable. "
            f"Reason: {exc.__class__.__name__}: {exc}"
        )


def calculate_risk_score(
    findings: list[dict[str, Any]],
    ai_act_check: dict[str, Any],
    gdpr_check: dict[str, Any],
) -> dict[str, int]:

    score = 0

    for finding in findings:
        if finding["risk_level"] == "High":
            score += 15
        elif finding["risk_level"] == "Medium":
            score += 8
        else:
            score += 3

    score += len(ai_act_check["missing_controls"]) * 4
    score += len(gdpr_check["missing_controls"]) * 4

    score = min(score, 100)

    return {
        "overall_risk_score": score,
        "gdpr_readiness_score": max(
            0,
            100 - len(gdpr_check["missing_controls"]) * 10,
        ),
        "eu_ai_act_readiness_score": max(
            0,
            100 - len(ai_act_check["missing_controls"]) * 10,
        ),
    }


def run_full_analysis(
    contract_text: str,
    use_llm: bool,
) -> dict[str, Any]:
    findings = detect_clauses(contract_text)

    ai_act_check = ai_act_compliance_check(contract_text)

    gdpr_check = gdpr_privacy_check(contract_text)

    risk_scores = calculate_risk_score(
        findings,
        ai_act_check,
        gdpr_check,
    )

    llm_summary = None

    if use_llm:
        llm_summary = generate_llm_summary(
            contract_text,
            findings,
            ai_act_check,
            gdpr_check,
        )

    return {
        "findings": findings,
        "risk_scores": risk_scores,
        "ai_act_check": ai_act_check,
        "gdpr_check": gdpr_check,
        "llm_summary": llm_summary,
    }


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes."""

    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text


def extract_text_from_docx_bytes(docx_bytes: bytes) -> str:
    """Extract text from DOCX bytes, including paragraphs and tables."""

    document = Document(BytesIO(docx_bytes))

    text_parts: list[str] = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    for table in document.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells]
            if any(row_text):
                text_parts.append(" | ".join(row_text))

    return "\n".join(text_parts)


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Dispatch to the correct extractor based on file extension."""

    lower_name = filename.lower()

    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf_bytes(file_bytes)

    if lower_name.endswith(".docx"):
        return extract_text_from_docx_bytes(file_bytes)

    raise ValueError(
        f"Unsupported file format: {filename}. "
        "Only PDF and DOCX files are currently supported."
    )


@app.post("/analyze-pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    use_llm: bool = False,
) -> dict[str, Any]:

    global latest_analysis 

    pdf_bytes = await file.read()

    contract_text = extract_text(pdf_bytes, file.filename)

    result = run_full_analysis(contract_text, use_llm)

    latest_analysis = {
        "findings": result["findings"],
        "risk_scores": result["risk_scores"],
        "ai_act_check": result["ai_act_check"],
        "gdpr_check": result["gdpr_check"],
        "llm_summary": result["llm_summary"],
    }


    return {
        "project": "Legal Clause Analyzer",
        "source": file.filename,
        "characters_analyzed": len(contract_text),
        "clause_findings": result["findings"],
        "ai_act_compliance_check": result["ai_act_check"],
        "gdpr_privacy_check": result["gdpr_check"],
        "risk_scores": result["risk_scores"],
        "llm_summary": result["llm_summary"],
        "disclaimer": (
            "This output is for compliance-readiness and "
            "demonstration only. It is not legal advice."
        ),
    }


@app.post("/analyze-docx")
async def analyze_docx(
    file: UploadFile = File(...),
    use_llm: bool = False,
) -> dict[str, Any]:

    global latest_analysis

    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only DOCX files are supported.",
        )

    docx_bytes = await file.read()

    contract_text = extract_text(docx_bytes, file.filename)

    result = run_full_analysis(contract_text, use_llm)

    latest_analysis = {
        "findings": result["findings"],
        "risk_scores": result["risk_scores"],
        "ai_act_check": result["ai_act_check"],
        "gdpr_check": result["gdpr_check"],
        "llm_summary": result["llm_summary"],
    }

    return {
        "project": "Legal Clause Analyzer",
        "source": file.filename,
        "characters_analyzed": len(contract_text),
        "clause_findings": result["findings"],
        "ai_act_compliance_check": result["ai_act_check"],
        "gdpr_privacy_check": result["gdpr_check"],
        "risk_scores": result["risk_scores"],
        "llm_summary": result["llm_summary"],
        "disclaimer": (
            "This output is for compliance-readiness and "
            "demonstration only. It is not legal advice."
        ),
    }


def generate_pdf_report(
    findings,
    risk_scores,
    ai_act_check,
    gdpr_check,
    llm_summary,
) -> BytesIO:

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    
    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph(
            "Legal Clause Analyzer Report",
            styles["Heading1"],
        )
    )

    story.append(
        Paragraph(
            "Professional Compliance Report",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            "Generated locally by Legal Clause Analyzer.",
            styles["BodyText"],
        )
    )

    story.append(
        Paragraph(
            "<br/><b>Risk Summary</b>",
            styles["Heading2"],
        )
    )

    overall = risk_scores["overall_risk_score"]
    gdpr = risk_scores["gdpr_readiness_score"]
    ai = risk_scores["eu_ai_act_readiness_score"]

    if overall >= 70:
        overall_color = colors.red
    elif overall >= 40:
        overall_color = colors.orange
    else:
        overall_color = colors.green

    if gdpr >= 80:
        gdpr_color = colors.green
    elif gdpr >= 50:
        gdpr_color = colors.orange
    else:
        gdpr_color = colors.red

    if ai >= 80:
        ai_color = colors.green
    elif ai >= 50:
        ai_color = colors.orange
    else:
        ai_color = colors.red

    score_table = [
        ["Metric", "Score"],
        ["Overall Risk", str(overall)],
        ["GDPR Readiness", str(gdpr)],
        ["EU AI Act Readiness", str(ai)],
    ]

    table = Table(
        score_table,
        colWidths=[3.8 * inch, 2 * inch],
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ("BOX", (0, 0), (-1, -1), 1, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, 3), "Helvetica-Bold"),
                ("TEXTCOLOR", (1, 1), (1, 1), overall_color),
                ("TEXTCOLOR", (1, 2), (1, 2), gdpr_color),
                ("TEXTCOLOR", (1, 3), (1, 3), ai_color),
            ]
        )
    )
    
    story.append(table)

    story.append(
        Paragraph(
            "<br/><b>Executive Summary</b>",
            styles["Heading2"],
        )
    )

    story.append(
        Paragraph(
            (
                "This report was generated locally using FastAPI and "
                "Llama 3. No contract text was transmitted to external "
                "cloud services."
            ),
            styles["BodyText"],
        )
    )

    story.append(
        Paragraph(
            (
                "This report is intended only as a compliance-readiness "
                "assessment and must not be considered legal advice."
            ),
            styles["BodyText"],
        )
    )

    story.append(
        Paragraph(
            "<br/><b>Detected Clauses</b>",
            styles["Heading2"],
        )
    )

    if findings:

        for finding in findings:

            story.append(
                Paragraph(
                    (
                        "<b>"
                        + finding["clause_type"]
                        + "</b>"
                        + " — Risk Level: "
                        + finding["risk_level"]
                    ),
                    styles["BodyText"],
                )
            )

            if "explanation" in finding:

                story.append(
                    Paragraph(
                        finding["explanation"],
                        styles["BodyText"],
                    )
                )

    else:

        story.append(
            Paragraph(
                "No legal clauses were detected.",
                styles["BodyText"],
            )
        )

    story.append(
        Paragraph(
            "<br/><b>GDPR Findings</b>",
            styles["Heading2"],
        )
    )

    for issue in gdpr_check["issues"]:

        story.append(
            Paragraph(
                "• " + issue,
                styles["BodyText"],
            )
        )

    story.append(
        Paragraph(
            "<br/><b>GDPR Recommendations</b>",
            styles["Heading3"],
        )
    )

    for recommendation in gdpr_check["recommendations"]:

        story.append(
            Paragraph(
                "• " + recommendation,
                styles["BodyText"],
            )
        )

    story.append(
        Paragraph(
            "<br/><b>EU AI Act Findings</b>",
            styles["Heading2"],
        )
    )

    for issue in ai_act_check["issues"]:

        story.append(
            Paragraph(
                "• " + issue,
                styles["BodyText"],
            )
        )

    story.append(
        Paragraph(
            "<br/><b>EU AI Act Recommendations</b>",
            styles["Heading3"],
        )
    )

    for recommendation in ai_act_check["recommendations"]:

        story.append(
            Paragraph(
                "• " + recommendation,
                styles["BodyText"],
            )
        )
    
    if llm_summary:
        story.append(
            Paragraph(
                "<br/><b>LLM Summary</b>",
                styles["Heading2"],
            )
        )

        story.append(
            Paragraph(
                llm_summary.replace("\n", "<br/>"),
                styles["BodyText"],
            )
        )
    
    
    document.build(story)
    buffer.seek(0)
    return buffer


@app.get("/download-report")
def download_report():

    global latest_analysis

    if not latest_analysis:
        return {
        "error": "No analysis available. Please analyze a PDF first."
    }

    findings = latest_analysis["findings"]
    risk_scores = latest_analysis["risk_scores"]
    ai_act_check = latest_analysis["ai_act_check"]
    gdpr_check = latest_analysis["gdpr_check"]
    llm_summary = latest_analysis["llm_summary"]

    pdf = generate_pdf_report(
        findings,
        risk_scores,
        ai_act_check,
        gdpr_check,
        llm_summary,
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
            "attachment; filename=Legal_Report.pdf"
        },
    )

      
@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "status": "ok",
        "project": "Legal Clause Analyzer",
        "docs": "/docs",
    }


@app.post("/analyze")
def analyze_contract(request: AnalyzeRequest) -> dict[str, Any]:
    result = run_full_analysis(request.contract_text, request.use_llm)

    return {
        "project": "Legal Clause Analyzer",
        "privacy_note": (
            "This prototype does not store contract text. "
            "Use synthetic or anonymized data for demos."
        ),
        "clause_findings": result["findings"],
        "ai_act_compliance_check": result["ai_act_check"],
        "gdpr_privacy_check": result["gdpr_check"],
        "risk_scores": result["risk_scores"],
        "llm_summary": result["llm_summary"],
        "disclaimer": (
            "This output is for compliance-readiness and product "
            "demonstration only. It is not legal advice."
        ),
    } 