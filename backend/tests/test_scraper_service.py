"""Tests for ScraperService — mocked dependencies."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.scraper_service import CrawlReport, LearnReport, ScraperService


# ---------------------------------------------------------------------------
# CrawlReport / LearnReport
# ---------------------------------------------------------------------------


def test_crawl_report_defaults():
    r = CrawlReport()
    assert r.sets_discovered == 0
    assert r.errors == []


def test_learn_report_defaults():
    r = LearnReport()
    assert r.url == ""
    assert r.success is False


# ---------------------------------------------------------------------------
# ScraperService — is_running guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_double_crawl_rejected():
    service = ScraperService()
    service._running = True
    report = await service.run_full_crawl()
    assert len(report.errors) == 1
    assert "already in progress" in report.errors[0].lower()


@pytest.mark.asyncio
async def test_not_running_initially():
    service = ScraperService()
    assert service.is_running is False


# ---------------------------------------------------------------------------
# ScraperService — run_full_crawl (mocked scraper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_crawl_mocked():
    mock_scrape = AsyncMock(return_value={
        "discovered": 10, "parsed": 8, "errors": 2, "dj_profiles": 3,
    })

    service = ScraperService(graph=None)

    with patch("scraper.tracklist_scraper.scrape", mock_scrape):
        report = await service.run_full_crawl(genres=["tech house"], max_sets=10)

    assert report.sets_discovered == 10
    assert report.sets_parsed == 8
    assert service.is_running is False


# ---------------------------------------------------------------------------
# ScraperService — learn_from_url (no actual network)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_learn_from_url_exception_handled():
    """When playwright import fails, report should indicate error."""
    service = ScraperService(graph=None)

    with patch("scraper.tracklist_scraper.parse_tracklist", side_effect=ImportError("no playwright")):
        with patch("playwright.async_api.async_playwright", side_effect=ImportError("no playwright")):
            report = await service.learn_from_url("https://example.com/tracklist/123")

    assert report.success is False
    assert report.error is not None
