"""Tests for the root endpoint and general API health."""

from fastapi.testclient import TestClient


def test_root_returns_200_and_expected_payload(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "project": "Legal Clause Analyzer",
        "docs": "/docs",
    }


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Legal Clause Analyzer"
    assert "/analyze" in schema["paths"]
    assert "/compare-contracts" in schema["paths"]
