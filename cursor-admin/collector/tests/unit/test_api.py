"""
API tests for main module: health, /api/sessions, and protected GET /api/* routes.
Uses mocked get_pool and skipped init_db/run_full_sync in lifespan.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(app_with_mocked_db, api_key):
    """TestClient with x-api-key header set."""
    return TestClient(
        app_with_mocked_db,
        headers={"x-api-key": api_key},
    )


def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_does_not_require_api_key(app_with_mocked_db):
    r = TestClient(app_with_mocked_db).get("/health")
    assert r.status_code == 200


def test_api_members_requires_api_key(app_with_mocked_db):
    r = TestClient(app_with_mocked_db).get("/api/members")
    assert r.status_code == 422 or r.status_code == 401


def test_api_members_returns_list_with_valid_key(client):
    r = client.get("/api/members")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_sessions_post_accepts_valid_payload(app_with_mocked_db):
    body = {
        "event": "session_end",
        "conversation_id": "conv-1",
        "user_email": "u@x.com",
        "machine_id": "m1",
        "workspace_roots": ["/path/to/proj"],
        "ended_at": 1709308800,
        "duration_seconds": 120,
    }
    r = TestClient(app_with_mocked_db).post("/api/sessions", json=body)
    assert r.status_code == 204


def test_api_sessions_post_accepts_project_id(app_with_mocked_db):
    """POST /api/sessions accepts optional project_id from Hook."""
    body = {
        "event": "session_end",
        "conversation_id": "conv-2",
        "user_email": "u@x.com",
        "workspace_roots": ["/path/to/proj"],
        "ended_at": 1709308800,
        "duration_seconds": 60,
        "project_id": 1,
    }
    r = TestClient(app_with_mocked_db).post("/api/sessions", json=body)
    assert r.status_code == 204


def test_api_usage_daily_returns_list(client):
    r = client.get("/api/usage/daily")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_sessions_summary_returns_list(client):
    r = client.get("/api/sessions/summary")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_alerts_rules_returns_list(client):
    r = client.get("/api/alerts/rules")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_alerts_events_returns_list(client):
    r = client.get("/api/alerts/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_projects_returns_list(client):
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_api_projects_whitelist_no_auth(app_with_mocked_db):
    """Whitelist is public (no API key) for Hook."""
    r = TestClient(app_with_mocked_db).get("/api/projects/whitelist")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert "rules" in data
    assert isinstance(data["rules"], list)


def test_api_projects_reinject_hook_404_when_project_missing(client):
    """POST /api/projects/{id}/reinject-hook returns 404 when project not found."""
    r = client.post("/api/projects/999/reinject-hook")
    assert r.status_code == 404


def test_api_projects_contributions_404_when_project_missing(client):
    """GET /api/projects/{id}/contributions returns 404 when project not found."""
    r = client.get("/api/projects/999/contributions")
    assert r.status_code == 404


def test_api_projects_summary_404_when_project_missing(client):
    """GET /api/projects/{id}/summary returns 404 when project not found."""
    r = client.get("/api/projects/999/summary")
    assert r.status_code == 404


def test_api_contributions_my_returns_list(client):
    """GET /api/contributions/my?email= returns list (member-facing)."""
    r = client.get("/api/contributions/my?email=user%40company.com")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
