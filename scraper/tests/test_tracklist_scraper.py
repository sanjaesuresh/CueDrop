"""Tests for tracklist_scraper — mocked Playwright, no network calls."""

from __future__ import annotations

from unittest.mock import patch

from scraper.tracklist_scraper import (
    QueueEntry,
    load_queue,
    sanitize_filename,
    save_queue,
)


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------


def test_sanitize_simple():
    assert sanitize_filename("Fisher") == "Fisher"


def test_sanitize_spaces():
    assert sanitize_filename("Chris Lake") == "Chris_Lake"


def test_sanitize_special_chars():
    assert sanitize_filename("CamelPhat & Elderbrook") == "CamelPhat___Elderbrook"


def test_sanitize_long_name():
    result = sanitize_filename("a" * 200)
    assert len(result) <= 100


def test_sanitize_empty():
    assert sanitize_filename("") == ""


# ---------------------------------------------------------------------------
# Queue persistence
# ---------------------------------------------------------------------------


def test_queue_roundtrip(tmp_path):
    queue_file = tmp_path / "queue.json"
    entries = [
        QueueEntry(url="https://example.com/1", status="done"),
        QueueEntry(url="https://example.com/2", status="pending"),
        QueueEntry(url="https://example.com/3", status="error", error="timeout"),
    ]

    with patch("scraper.tracklist_scraper.QUEUE_PATH", queue_file):
        save_queue(entries)
        loaded = load_queue()

    assert len(loaded) == 3
    assert loaded[0].url == "https://example.com/1"
    assert loaded[0].status == "done"
    assert loaded[2].status == "error"
    assert loaded[2].error == "timeout"


def test_load_queue_missing_file(tmp_path):
    missing = tmp_path / "nonexistent.json"
    with patch("scraper.tracklist_scraper.QUEUE_PATH", missing):
        result = load_queue()
    assert result == []


# ---------------------------------------------------------------------------
# QueueEntry dataclass
# ---------------------------------------------------------------------------


def test_queue_entry_defaults():
    e = QueueEntry(url="https://example.com")
    assert e.status == "pending"
    assert e.error is None


def test_queue_entry_custom():
    e = QueueEntry(url="https://example.com", status="done", error=None)
    assert e.status == "done"
