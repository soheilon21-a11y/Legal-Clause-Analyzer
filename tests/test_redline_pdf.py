"""Tests for redline PDF report generation (``redlining.pdf_report``).

Verifies that the PDF is produced correctly, contains expected
sections, and handles both empty and populated suggestion lists.
"""

import fitz

from redlining.models import RedlineResult, RedlineSuggestion
from redlining.pdf_report import generate_redline_pdf


def _make_suggestion(clause_type: str = "Termination") -> RedlineSuggestion:
    return RedlineSuggestion(
        clause_type=clause_type,
        original_clause="Original clause text.",
        suggested_clause="Improved clause text.",
        reason="Test reason.",
        risk_level="High",
        confidence_score=0.85,
        negotiable=True,
        playbook_source="test_pb",
        jurisdiction="Test",
    )


def _make_result(
    suggestions: list[RedlineSuggestion] | None = None,
) -> RedlineResult:
    return RedlineResult(
        suggestions=suggestions or [],
        total_clauses_scanned=10,
        negotiable_clauses_found=len(suggestions or []),
        playbooks_used=["test_pb"],
    )


class TestGenerateRedlinePdf:
    def test_produces_valid_pdf_with_suggestions(self) -> None:
        result = _make_result([_make_suggestion()])
        buffer = generate_redline_pdf(result, "test_contract.docx")

        buffer.seek(0)
        doc = fitz.open(stream=buffer.read(), filetype="pdf")
        assert doc.page_count >= 1

        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        assert "Redline Analysis Report" in full_text
        assert "test_contract.docx" in full_text
        assert "Termination" in full_text
        assert "Disclaimer" in full_text

    def test_produces_valid_pdf_without_suggestions(self) -> None:
        result = _make_result([])
        buffer = generate_redline_pdf(result, "empty_contract.txt")

        buffer.seek(0)
        doc = fitz.open(stream=buffer.read(), filetype="pdf")
        assert doc.page_count >= 1

        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        assert "No negotiable clauses" in full_text

    def test_multiple_suggestions_all_present(self) -> None:
        suggestions = [
            _make_suggestion("Termination"),
            _make_suggestion("Confidentiality"),
            _make_suggestion("Data Protection"),
        ]
        result = _make_result(suggestions)
        buffer = generate_redline_pdf(result, "multi.docx")

        buffer.seek(0)
        doc = fitz.open(stream=buffer.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        for s in suggestions:
            assert s.clause_type in full_text

    def test_summary_metrics_present(self) -> None:
        result = _make_result([_make_suggestion()])
        buffer = generate_redline_pdf(result, "test.txt")

        buffer.seek(0)
        doc = fitz.open(stream=buffer.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        assert "Total clauses scanned" in full_text
        assert "Negotiable clauses found" in full_text
        assert "Playbooks used" in full_text
