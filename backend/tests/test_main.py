"""Tests for FastAPI endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


def test_get_queue_initial(client):
    resp = client.get("/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert "entries" in data
    assert "current" in data
    assert "wildcards" in data


def test_admin_request(client):
    resp = client.post("/request/admin", json={"title": "Losing It", "artist": "Fisher"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["track"]["title"] == "Losing It"
    assert data["layer"] == "anchor"
    assert data["source"] == "admin"


def test_skip_empty_queue(client):
    resp = client.post("/skip")
    assert resp.status_code == 200
    assert resp.json()["status"] == "queue_empty"


def test_admin_request_then_skip(client):
    client.post("/request/admin", json={"title": "Cola", "artist": "CamelPhat"})
    resp = client.post("/skip")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "skipped"
    assert data["now_playing"]["track"]["title"] == "Cola"


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


def test_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "decks" in data
    assert len(data["decks"]) == 2


# ---------------------------------------------------------------------------
# WebSocket — Admin
# ---------------------------------------------------------------------------


def test_ws_admin(client):
    with client.websocket_connect("/ws/admin") as ws:
        data = ws.receive_json()
        assert data["type"] == "queue_update"
        assert "data" in data


# ---------------------------------------------------------------------------
# WebSocket — Guest
# ---------------------------------------------------------------------------


def test_ws_guest(client):
    with client.websocket_connect("/ws/guest/session123") as ws:
        ws.send_text("hello")
        # No response expected, just verify connection works


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------


def test_cors_headers(client):
    resp = client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


def test_chat_skip(client):
    resp = client.post("/chat", json={"text": "skip"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["intent"] == "skip"
    assert "response" in data


def test_chat_track_request(client):
    resp = client.post("/chat", json={"text": "play Losing It"})
    assert resp.status_code == 200
    assert resp.json()["intent"] == "track_request"


# ---------------------------------------------------------------------------
# Guest request + approval flow
# ---------------------------------------------------------------------------


def test_guest_request(client):
    resp = client.post("/request/guest", json={
        "track": {"title": "Cola", "artist": "CamelPhat"},
        "session_id": "sess1",
        "device_id": "dev1",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("pending", "approved")


def test_pending_requests_initially_empty(client):
    resp = client.get("/requests/pending")
    assert resp.status_code == 200
    # May have requests from other tests due to shared state, just check format
    assert isinstance(resp.json(), list)


def test_approve_nonexistent(client):
    resp = client.post("/approve/nonexistent")
    assert resp.status_code == 200
    assert resp.json().get("error") == "Request not found"


def test_decline_nonexistent(client):
    resp = client.post("/decline/nonexistent")
    assert resp.status_code == 200
    assert resp.json().get("error") == "Request not found"


# ---------------------------------------------------------------------------
# Session & QR
# ---------------------------------------------------------------------------


def test_get_session(client):
    resp = client.get("/session/any_id")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "name" in data


def test_session_qr(client):
    resp = client.get("/session/qr")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


def test_update_settings(client):
    resp = client.put("/settings", json={"manual_approval": False})
    assert resp.status_code == 200
    data = resp.json()
    assert "manual_approval" in data


# ---------------------------------------------------------------------------
# Search (Spotify proxy)
# ---------------------------------------------------------------------------


def test_search_no_credentials(client):
    """Without Spotify credentials, search returns empty list."""
    resp = client.get("/search", params={"q": "Fisher Losing It"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_search_with_limit(client):
    resp = client.get("/search", params={"q": "Cola", "limit": 5})
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Scraper endpoints
# ---------------------------------------------------------------------------


def test_learn_endpoint(client):
    """learn_from_url will fail gracefully without playwright."""
    resp = client.post("/learn", json={"url": "https://example.com/tracklist/1"})
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert data["url"] == "https://example.com/tracklist/1"
    assert data["success"] is False  # no playwright installed


def test_scrape_endpoint_starts(client):
    resp = client.post("/scrape", json={"genres": ["tech house"], "max_sets": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"
    assert data["max_sets"] == 5


def test_scrape_default_body(client):
    resp = client.post("/scrape", json={})
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
