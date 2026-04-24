"""Tests for ACRCloud fingerprinter — no network calls."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scraper.fingerprinter import (
    ACRCloudFingerprinter,
    FingerprintMatch,
    FingerprintResult,
)


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


def test_fingerprint_match_defaults():
    m = FingerprintMatch(title="Cola", artist="CamelPhat")
    assert m.title == "Cola"
    assert m.confidence == 0.0
    assert m.timestamp_s == 0.0


def test_fingerprint_result_defaults():
    r = FingerprintResult()
    assert r.matches == []
    assert r.success is False
    assert r.error is None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_is_configured_false():
    fp = ACRCloudFingerprinter()
    assert fp.is_configured is False


def test_is_configured_true():
    fp = ACRCloudFingerprinter(
        access_key="key", access_secret="secret", host="example.com"
    )
    assert fp.is_configured is True


def test_is_configured_partial():
    fp = ACRCloudFingerprinter(access_key="key")
    assert fp.is_configured is False


# ---------------------------------------------------------------------------
# identify — not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_not_configured():
    fp = ACRCloudFingerprinter()
    result = await fp.identify(b"fake audio data")
    assert result.success is False
    assert "not configured" in result.error


# ---------------------------------------------------------------------------
# identify_file — file not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_file_not_found():
    fp = ACRCloudFingerprinter(access_key="k", access_secret="s")
    result = await fp.identify_file("/nonexistent/file.wav")
    assert result.error is not None
    assert "not found" in result.error.lower()


# ---------------------------------------------------------------------------
# identify — mocked HTTP
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_identify_success():
    fp = ACRCloudFingerprinter(access_key="k", access_secret="s", host="test.acrcloud.com")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": {"code": 0, "msg": "Success"},
        "metadata": {
            "music": [
                {
                    "title": "Losing It",
                    "artists": [{"name": "Fisher"}],
                    "album": {"name": "Losing It EP"},
                    "acrid": "abc123",
                    "score": 95,
                    "duration_ms": 300000,
                }
            ]
        },
    }

    with patch.object(fp._http, "post", AsyncMock(return_value=mock_response)):
        result = await fp.identify(b"fake audio")

    assert result.success is True
    assert len(result.matches) == 1
    assert result.matches[0].title == "Losing It"
    assert result.matches[0].artist == "Fisher"
    assert result.matches[0].confidence == 95.0
    assert result.matches[0].acrid == "abc123"


@pytest.mark.asyncio
async def test_identify_no_match():
    fp = ACRCloudFingerprinter(access_key="k", access_secret="s", host="test.acrcloud.com")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": {"code": 1001, "msg": "No result"},
    }

    with patch.object(fp._http, "post", AsyncMock(return_value=mock_response)):
        result = await fp.identify(b"noise")

    assert result.success is True
    assert len(result.matches) == 0


@pytest.mark.asyncio
async def test_identify_api_error():
    fp = ACRCloudFingerprinter(access_key="k", access_secret="s", host="test.acrcloud.com")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": {"code": 3000, "msg": "Invalid key"},
    }

    with patch.object(fp._http, "post", AsyncMock(return_value=mock_response)):
        result = await fp.identify(b"audio")

    assert result.success is False
    assert result.error == "Invalid key"


@pytest.mark.asyncio
async def test_identify_network_exception():
    fp = ACRCloudFingerprinter(access_key="k", access_secret="s", host="test.acrcloud.com")

    with patch.object(fp._http, "post", side_effect=Exception("Connection refused")):
        result = await fp.identify(b"audio")

    assert result.success is False
    assert "Connection refused" in result.error


# ---------------------------------------------------------------------------
# scan_at_intervals — not configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scan_not_configured():
    fp = ACRCloudFingerprinter()
    matches = await fp.scan_at_intervals("/fake/file.wav")
    assert matches == []


# ---------------------------------------------------------------------------
# Signature building
# ---------------------------------------------------------------------------


def test_build_signature():
    fp = ACRCloudFingerprinter(access_key="testkey", access_secret="testsecret")
    sig = fp._build_signature("1234567890")
    assert isinstance(sig, str)
    assert len(sig) > 0  # base64 encoded


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close():
    fp = ACRCloudFingerprinter()
    await fp.close()  # should not raise
