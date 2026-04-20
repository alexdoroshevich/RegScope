"""Unit tests for the /health endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app


def test_health_returns_200() -> None:
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200


def test_health_body() -> None:
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert body == {"status": "ok"}
