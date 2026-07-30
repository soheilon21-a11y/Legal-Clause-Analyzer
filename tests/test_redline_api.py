"""Tests for the redlining API endpoints.

Covers ``GET /playbooks``, ``POST /redline``, ``POST /redline-pdf``,
and ``GET /download-redline-report``. All tests use the real FastAPI
``TestClient`` without a running LLM.
"""

from collections.abc import Callable

from fastapi.testclient import TestClient

REDLINE_CONTRACT_TEXT = (
    "This agreement contains a limitation of liability provision "
    "capping all liability. Either party may terminate this agreement "
    "with thirty days written notice. Both parties must protect "
    "confidential information at all times. The processor may handle "
    "personal data in line with GDPR and applicable data protection law."
)

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

PDF_MEDIA_TYPE = "application/pdf"

REDLINE_RESULT_KEYS = {
    "suggestions",
    "total_clauses_scanned",
    "negotiable_clauses_found",
    "playbooks_used",
    "disclaimer",
}


class TestListPlaybooks:
    def test_returns_expected_structure(self, client: TestClient) -> None:
        response = client.get("/playbooks")
        assert response.status_code == 200

        payload = response.json()
        assert payload["project"] == "Legal Clause Analyzer"
        assert isinstance(payload["playbooks"], list)
        assert payload["total"] >= 2

        for pb in payload["playbooks"]:
            assert "playbook_id" in pb
            assert "playbook_name" in pb
            assert "jurisdiction" in pb
            assert "version" in pb
            assert isinstance(pb["rules_count"], int)
            assert pb["rules_count"] >= 1

    def test_known_playbooks_present(self, client: TestClient) -> None:
        response = client.get("/playbooks")
        ids = {pb["playbook_id"] for pb in response.json()["playbooks"]}
        assert "us_general_commercial" in ids
        assert "eu_general_commercial" in ids


class TestRedlineEndpoint:
    def test_returns_redline_suggestions(self, client: TestClient) -> None:
        response = client.post(
            "/redline",
            json={
                "contract_text": REDLINE_CONTRACT_TEXT,
                "use_llm": False,
            },
        )
        assert response.status_code == 200

        payload = response.json()
        assert payload["project"] == "Legal Clause Analyzer"
        assert payload["source"] == "text_input"
        assert REDLINE_RESULT_KEYS <= payload["redline_result"].keys()

        result = payload["redline_result"]
        assert result["total_clauses_scanned"] > 0
        assert result["negotiable_clauses_found"] > 0
        assert len(result["suggestions"]) > 0

        for suggestion in result["suggestions"]:
            assert "clause_type" in suggestion
            assert "original_clause" in suggestion
            assert "suggested_clause" in suggestion
            assert "reason" in suggestion
            assert suggestion["risk_level"] in {"Low", "Medium", "High", "Critical"}
            assert 0.0 <= suggestion["confidence_score"] <= 1.0

    def test_playbook_filter(self, client: TestClient) -> None:
        response = client.post(
            "/redline",
            json={
                "contract_text": REDLINE_CONTRACT_TEXT,
                "playbook_ids": ["us_general_commercial"],
                "use_llm": False,
            },
        )
        assert response.status_code == 200
        result = response.json()["redline_result"]
        assert result["playbooks_used"] == ["us_general_commercial"]

    def test_rejects_short_text(self, client: TestClient) -> None:
        response = client.post(
            "/redline",
            json={"contract_text": "too short", "use_llm": False},
        )
        assert response.status_code == 422

    def test_no_clauses_in_plain_text(self, client: TestClient) -> None:
        response = client.post(
            "/redline",
            json={
                "contract_text": (
                    "This agreement sets out general cooperation "
                    "between the two companies regarding quarterly "
                    "planning and shared logistics."
                ),
                "use_llm": False,
            },
        )
        assert response.status_code == 200
        result = response.json()["redline_result"]
        assert result["suggestions"] == []
        assert result["negotiable_clauses_found"] == 0

    def test_suggestions_sorted_by_risk(self, client: TestClient) -> None:
        response = client.post(
            "/redline",
            json={
                "contract_text": REDLINE_CONTRACT_TEXT,
                "use_llm": False,
            },
        )
        result = response.json()["redline_result"]
        risk_order = {
            "Critical": 0, "High": 1, "Medium": 2, "Low": 3
        }
        levels = [
            risk_order.get(s["risk_level"], 4)
            for s in result["suggestions"]
        ]
        assert levels == sorted(levels)


class TestRedlinePdfEndpoint:
    def test_docx_upload(self, client: TestClient, docx_factory: Callable[[str], bytes]) -> None:
        files = {
            "file": ("contract.docx", docx_factory(REDLINE_CONTRACT_TEXT), DOCX_MEDIA_TYPE),
        }
        response = client.post("/redline-pdf", files=files)
        assert response.status_code == 200

        payload = response.json()
        assert payload["project"] == "Legal Clause Analyzer"
        assert payload["source"] == "contract.docx"
        assert payload["characters_analyzed"] > 0
        assert REDLINE_RESULT_KEYS <= payload["redline_result"].keys()

    def test_pdf_upload(self, client: TestClient, pdf_factory: Callable[[str], bytes]) -> None:
        files = {
            "file": ("contract.pdf", pdf_factory(REDLINE_CONTRACT_TEXT), PDF_MEDIA_TYPE),
        }
        response = client.post("/redline-pdf", files=files)
        assert response.status_code == 200
        assert response.json()["source"] == "contract.pdf"

    def test_rejects_unsupported_type(self, client: TestClient) -> None:
        files = {
            "file": ("contract.txt", b"plain text content", "text/plain"),
        }
        response = client.post("/redline-pdf", files=files)
        assert response.status_code == 400

    def test_playbook_ids_query_param(
        self, client: TestClient, docx_factory: Callable[[str], bytes]
    ) -> None:
        files = {
            "file": ("contract.docx", docx_factory(REDLINE_CONTRACT_TEXT), DOCX_MEDIA_TYPE),
        }
        response = client.post(
            "/redline-pdf",
            files=files,
            params={"playbook_ids": "us_general_commercial"},
        )
        assert response.status_code == 200
        result = response.json()["redline_result"]
        assert result["playbooks_used"] == ["us_general_commercial"]


class TestDownloadRedlineReport:
    def test_returns_404_without_prior_analysis(self, client: TestClient) -> None:
        import main
        main.latest_redline = None

        response = client.get("/download-redline-report")
        assert response.status_code == 404
        assert "No redline analysis available" in response.json()["detail"]

    def test_returns_pdf_after_analysis(self, client: TestClient) -> None:
        client.post(
            "/redline",
            json={
                "contract_text": REDLINE_CONTRACT_TEXT,
                "use_llm": False,
            },
        )

        response = client.get("/download-redline-report")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 100
