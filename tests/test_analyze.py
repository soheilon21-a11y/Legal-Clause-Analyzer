"""Tests for the POST /analyze endpoint using the rule-based path.

All tests call the endpoint with ``use_llm=False`` so they never depend
on a running local LLM and only exercise the deterministic analysis.
"""

from fastapi.testclient import TestClient

ANALYSIS_RESPONSE_KEYS = {
    "project",
    "privacy_note",
    "clause_findings",
    "ai_act_compliance_check",
    "gdpr_privacy_check",
    "risk_scores",
    "llm_summary",
    "disclaimer",
}

RISK_SCORE_KEYS = {
    "overall_risk_score",
    "gdpr_readiness_score",
    "eu_ai_act_readiness_score",
}

AI_ACT_CHECK_KEYS = {
    "ai_act_triggered",
    "matched_ai_terms",
    "matched_high_risk_terms",
    "missing_controls",
    "issues",
    "recommendations",
    "summary",
}

GDPR_CHECK_KEYS = {
    "personal_data_detected",
    "sensitive_data_detected",
    "matched_personal_data_terms",
    "matched_sensitive_data_terms",
    "missing_controls",
    "issues",
    "recommendations",
}

AI_CONTRACT_TEXT = (
    "The vendor provides an artificial intelligence system based on "
    "machine learning for automated decision-making support services."
)


def _post_analyze(
    client: TestClient,
    contract_text: str,
    use_llm: bool = False,
) -> dict:
    response = client.post(
        "/analyze",
        json={"contract_text": contract_text, "use_llm": use_llm},
    )
    assert response.status_code == 200
    return response.json()


def test_analyze_returns_expected_response_structure(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    payload = _post_analyze(client, sample_contract_text)

    assert ANALYSIS_RESPONSE_KEYS <= payload.keys()
    assert payload["project"] == "Legal Clause Analyzer"
    assert isinstance(payload["privacy_note"], str)
    assert isinstance(payload["disclaimer"], str)
    assert isinstance(payload["clause_findings"], list)
    assert AI_ACT_CHECK_KEYS <= payload["ai_act_compliance_check"].keys()
    assert GDPR_CHECK_KEYS <= payload["gdpr_privacy_check"].keys()
    assert RISK_SCORE_KEYS <= payload["risk_scores"].keys()


def test_analyze_with_llm_disabled_returns_no_summary(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    payload = _post_analyze(client, sample_contract_text, use_llm=False)

    assert payload["llm_summary"] is None


def test_analyze_detects_expected_clause_types(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    payload = _post_analyze(client, sample_contract_text)

    findings = payload["clause_findings"]
    detected_types = {finding["clause_type"] for finding in findings}

    assert {
        "Liability Limitation",
        "Termination",
        "Confidentiality",
        "Data Protection",
    } <= detected_types

    for finding in findings:
        assert isinstance(finding["clause_type"], str)
        assert finding["risk_level"] in {"Low", "Medium", "High"}
        assert finding["matched_keywords"]
        assert all(
            isinstance(keyword, str)
            for keyword in finding["matched_keywords"]
        )
        assert isinstance(finding["explanation"], str)


def test_analyze_detects_no_clauses_in_plain_text(
    client: TestClient,
    plain_contract_text: str,
) -> None:
    payload = _post_analyze(client, plain_contract_text)

    assert payload["clause_findings"] == []


def test_analyze_gdpr_check_flags_personal_data(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    gdpr_check = _post_analyze(client, sample_contract_text)[
        "gdpr_privacy_check"
    ]

    assert gdpr_check["personal_data_detected"] is True
    assert "personal data" in gdpr_check["matched_personal_data_terms"]
    assert isinstance(gdpr_check["sensitive_data_detected"], bool)
    assert isinstance(gdpr_check["missing_controls"], list)
    assert gdpr_check["issues"]
    assert gdpr_check["recommendations"]


def test_analyze_ai_act_check_triggered_by_ai_terms(
    client: TestClient,
) -> None:
    ai_act_check = _post_analyze(client, AI_CONTRACT_TEXT)[
        "ai_act_compliance_check"
    ]

    assert ai_act_check["ai_act_triggered"] is True
    assert "artificial intelligence" in ai_act_check["matched_ai_terms"]
    assert isinstance(ai_act_check["missing_controls"], list)
    assert ai_act_check["issues"]
    assert ai_act_check["recommendations"]
    assert isinstance(ai_act_check["summary"], str)


def test_analyze_ai_act_check_not_triggered_without_ai_terms(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    ai_act_check = _post_analyze(client, sample_contract_text)[
        "ai_act_compliance_check"
    ]

    assert ai_act_check["ai_act_triggered"] is False
    assert ai_act_check["matched_ai_terms"] == []
    assert ai_act_check["missing_controls"] == []


def test_analyze_risk_scores_are_integers_within_bounds(
    client: TestClient,
    sample_contract_text: str,
) -> None:
    risk_scores = _post_analyze(client, sample_contract_text)["risk_scores"]

    for key in RISK_SCORE_KEYS:
        score = risk_scores[key]
        assert isinstance(score, int)
        assert 0 <= score <= 100


def test_analyze_rejects_too_short_contract_text(
    client: TestClient,
) -> None:
    response = client.post(
        "/analyze",
        json={"contract_text": "too short", "use_llm": False},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_analyze_rejects_missing_contract_text(
    client: TestClient,
) -> None:
    response = client.post("/analyze", json={"use_llm": False})

    assert response.status_code == 422
