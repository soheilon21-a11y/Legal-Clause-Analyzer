"""Shared pytest fixtures for the Legal Clause Analyzer test suite.

The fixtures here only wire the existing FastAPI application into a
``TestClient`` and provide small synthetic contract texts. They do not
patch, mock, or alter any application logic.
"""

from collections.abc import Callable
from io import BytesIO

import fitz
import pytest
from docx import Document
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Return a reusable FastAPI ``TestClient`` bound to the application."""
    return TestClient(app)


@pytest.fixture()
def sample_contract_text() -> str:
    """Synthetic contract text covering several rule-based clause types."""
    return (
        "This agreement contains a limitation of liability provision "
        "capping all liability. Either party may terminate this agreement "
        "with thirty days written notice. Both parties must protect "
        "confidential information at all times. The processor may handle "
        "personal data in line with GDPR and applicable data protection "
        "law."
    )


@pytest.fixture()
def plain_contract_text() -> str:
    """Synthetic contract text that matches none of the known keywords."""
    return (
        "This agreement sets out general cooperation between the two "
        "companies regarding quarterly planning and shared logistics."
    )


@pytest.fixture()
def docx_factory() -> Callable[[str], bytes]:
    """Return a factory that builds in-memory DOCX bytes from plain text."""

    def _make_docx(text: str) -> bytes:
        document = Document()
        document.add_paragraph(text)
        buffer = BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    return _make_docx


@pytest.fixture()
def pdf_factory() -> Callable[[str], bytes]:
    """Return a factory that builds a one-page in-memory PDF from text."""

    def _make_pdf(text: str) -> bytes:
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), text)
        pdf_bytes = document.tobytes()
        document.close()
        return pdf_bytes

    return _make_pdf
