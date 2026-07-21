"""Tests for the POST /compare-contracts endpoint.

Both contracts are synthetic DOCX documents built in memory, so the
tests exercise the real upload, text-extraction, and comparison flow
without relying on external files or a running LLM.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient

CONTRACT_A_TEXT = (
    "Either party may terminate this agreement with thirty days written "
    "notice. This agreement also contains a limitation of liability "
    "provision capping all liability."
)

CONTRACT_B_TEXT = (
    "Both parties must protect confidential information at all times. "
    "The processor may handle personal data in line with GDPR."
)

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

PDF_MEDIA_TYPE = "application/pdf"

PDF_CONTRACT_TEXT = (
    "Either party may terminate this agreement with thirty days notice."
)

RESPONSE_KEYS = {
    "project",
    "contract_a_filename",
    "contract_b_filename",
    "characters_extracted",
    "contract_a_analysis",
    "contract_b_analysis",
    "comparison",
    "disclaimer",
}

ANALYSIS_KEYS = {
    "findings",
    "risk_scores",
    "ai_act_check",
    "gdpr_check",
    "llm_summary",
}

CLAUSE_COMPARISON_KEYS = {
    "contract_a_clause_types",
    "contract_b_clause_types",
    "added",
    "removed",
    "common",
}

SCORE_COMPARISON_KEYS = {
    "overall_risk_score",
    "gdpr_readiness_score",
    "eu_ai_act_readiness_score",
}

SUMMARY_KEYS = {
    "added_clauses_count",
    "removed_clauses_count",
    "common_clauses_count",
    "total_clauses_contract_a",
    "total_clauses_contract_b",
}


def _post_compare(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
    text_a: str = CONTRACT_A_TEXT,
    text_b: str = CONTRACT_B_TEXT,
) -> dict:
    files = {
        "file_a": ("contract_a.docx", docx_factory(text_a), DOCX_MEDIA_TYPE),
        "file_b": ("contract_b.docx", docx_factory(text_b), DOCX_MEDIA_TYPE),
    }
    response = client.post("/compare-contracts", files=files)
    assert response.status_code == 200
    return response.json()


def test_compare_returns_expected_response_structure(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    payload = _post_compare(client, docx_factory)

    assert RESPONSE_KEYS <= payload.keys()
    assert payload["project"] == "Legal Clause Analyzer"
    assert payload["contract_a_filename"] == "contract_a.docx"
    assert payload["contract_b_filename"] == "contract_b.docx"
    assert isinstance(payload["disclaimer"], str)
    assert ANALYSIS_KEYS <= payload["contract_a_analysis"].keys()
    assert ANALYSIS_KEYS <= payload["contract_b_analysis"].keys()
    assert payload["contract_a_analysis"]["llm_summary"] is None
    assert payload["contract_b_analysis"]["llm_summary"] is None


def test_compare_reports_characters_extracted_consistently(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    extracted = _post_compare(client, docx_factory)["characters_extracted"]

    assert extracted.keys() == {"contract_a", "contract_b", "total"}
    assert isinstance(extracted["contract_a"], int)
    assert isinstance(extracted["contract_b"], int)
    assert extracted["contract_a"] > 0
    assert extracted["contract_b"] > 0
    assert (
        extracted["total"]
        == extracted["contract_a"] + extracted["contract_b"]
    )


def test_compare_detects_added_and_removed_clauses(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    comparison = _post_compare(client, docx_factory)["comparison"]

    clause_comparison = comparison["clause_comparison"]
    assert CLAUSE_COMPARISON_KEYS <= clause_comparison.keys()

    assert "Termination" in clause_comparison["removed"]
    assert "Liability Limitation" in clause_comparison["removed"]
    assert "Confidentiality" in clause_comparison["added"]
    assert "Data Protection" in clause_comparison["added"]
    assert clause_comparison["common"] == []

    summary = comparison["summary"]
    assert SUMMARY_KEYS <= summary.keys()
    assert summary["added_clauses_count"] == len(clause_comparison["added"])
    assert summary["removed_clauses_count"] == len(
        clause_comparison["removed"]
    )
    assert summary["common_clauses_count"] == len(clause_comparison["common"])
    assert summary["total_clauses_contract_a"] == len(
        clause_comparison["contract_a_clause_types"]
    )
    assert summary["total_clauses_contract_b"] == len(
        clause_comparison["contract_b_clause_types"]
    )


def test_compare_detects_common_clauses(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    shared_text = (
        "Either party may terminate this agreement with thirty days "
        "written notice."
    )
    comparison = _post_compare(
        client,
        docx_factory,
        text_a=shared_text,
        text_b=shared_text,
    )["comparison"]

    clause_comparison = comparison["clause_comparison"]
    assert "Termination" in clause_comparison["common"]
    assert clause_comparison["added"] == []
    assert clause_comparison["removed"] == []
    assert comparison["summary"]["common_clauses_count"] >= 1


def test_compare_score_comparison_structure_and_consistency(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    score_comparison = _post_compare(client, docx_factory)["comparison"][
        "score_comparison"
    ]

    assert SCORE_COMPARISON_KEYS <= score_comparison.keys()
    for metric in SCORE_COMPARISON_KEYS:
        delta = score_comparison[metric]
        assert isinstance(delta["contract_a"], int)
        assert isinstance(delta["contract_b"], int)
        assert delta["difference"] == delta["contract_b"] - delta["contract_a"]
        assert delta["trend"] in {"increased", "decreased", "unchanged"}


def test_compare_rejects_unsupported_file_type(
    client: TestClient,
    docx_factory: Callable[[str], bytes],
) -> None:
    files = {
        "file_a": ("contract_a.txt", b"plain text contract", "text/plain"),
        "file_b": (
            "contract_b.docx",
            docx_factory(CONTRACT_B_TEXT),
            DOCX_MEDIA_TYPE,
        ),
    }
    response = client.post("/compare-contracts", files=files)

    assert response.status_code == 400
    assert "Contract A" in response.json()["detail"]


def test_compare_supports_pdf_upload(
    client: TestClient,
    pdf_factory: Callable[[str], bytes],
    docx_factory: Callable[[str], bytes],
) -> None:
    files = {
        "file_a": (
            "contract_a.pdf",
            pdf_factory(PDF_CONTRACT_TEXT),
            PDF_MEDIA_TYPE,
        ),
        "file_b": (
            "contract_b.docx",
            docx_factory(CONTRACT_B_TEXT),
            DOCX_MEDIA_TYPE,
        ),
    }
    response = client.post("/compare-contracts", files=files)

    assert response.status_code == 200
    payload = response.json()
    assert payload["contract_a_filename"] == "contract_a.pdf"
    assert payload["characters_extracted"]["contract_a"] > 0
    clause_types_a = {
        finding["clause_type"]
        for finding in payload["contract_a_analysis"]["findings"]
    }
    assert "Termination" in clause_types_a
