"""Tests for QR generator."""

from __future__ import annotations

from backend.qr_generator import generate


def test_generate_returns_png_bytes():
    data = generate("session123")
    assert isinstance(data, bytes)
    assert len(data) > 0
    # PNG magic bytes
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_custom_base_url():
    data = generate("abc", base_url="https://myparty.ngrok.io")
    assert isinstance(data, bytes)
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_generate_different_sessions_differ():
    a = generate("session_a")
    b = generate("session_b")
    assert a != b
