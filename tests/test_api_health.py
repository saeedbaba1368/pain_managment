"""Smoke test: the FastAPI app must import cleanly and serve /health without
touching the database (SQLAlchemy engines connect lazily, so this catches
import-time errors -- circular imports, missing dependencies, broken
router wiring -- without needing Postgres running)."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_endpoint():
    from api.main import api

    client = TestClient(api)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_protected_endpoint_rejects_unauthenticated_request():
    from api.main import api

    client = TestClient(api)
    response = client.get("/patients")

    assert response.status_code in (401, 403)
