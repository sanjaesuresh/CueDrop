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
