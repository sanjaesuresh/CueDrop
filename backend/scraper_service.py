"""Scraping orchestrator — wraps scraper pipeline for API use."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

from backend.graph_client import GraphClient
from backend.import_pipeline import import_directory, import_file

logger = logging.getLogger(__name__)


@dataclass
class CrawlReport:
    """Results from a full crawl run."""

    sets_discovered: int = 0
    sets_parsed: int = 0
    tracks_imported: int = 0
    transitions_created: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class LearnReport:
    """Results from learning a single URL."""

    url: str = ""
    tracks_found: int = 0
    transitions_created: int = 0
    success: bool = False
    error: str | None = None


class ScraperService:
    """Orchestrates scraping and graph import."""

    def __init__(self, graph: GraphClient | None = None) -> None:
        self._graph = graph
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        return self._running

    async def run_full_crawl(
        self,
        genres: list[str] | None = None,
        max_sets: int = 100,
        output_dir: str = "scraper/output",
    ) -> CrawlReport:
        """Run a full scraping crawl and import results into the graph."""
        report = CrawlReport()

        if self._running:
            report.errors.append("Crawl already in progress")
            return report

        self._running = True
        try:
            from scraper.tracklist_scraper import scrape

            for genre in (genres or ["tech house"]):
                stats = await scrape(genre=genre, max_sets=max_sets, output_dir=output_dir)
                report.sets_discovered += stats.get("discovered", 0)
                report.sets_parsed += stats.get("parsed", 0)

            # Import scraped output into graph
            if self._graph:
                out_path = Path(output_dir)
                if out_path.is_dir():
                    result = await import_directory(output_dir, self._graph)
                    report.tracks_imported = result.tracks_added
                    report.transitions_created = result.transitions_created
                    report.errors.extend(result.errors)

        except Exception as exc:
            logger.exception("Crawl failed")
            report.errors.append(str(exc))
        finally:
            self._running = False

        return report

    async def learn_from_url(self, url: str) -> LearnReport:
        """Parse a single tracklist URL and import into the graph."""
        report = LearnReport(url=url)

        try:
            from scraper.tracklist_scraper import parse_tracklist
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                page = await browser.new_page()

                set_data = await parse_tracklist(page, url)
                await browser.close()

            if set_data is None:
                report.error = "Could not parse tracklist from URL"
                return report

            report.tracks_found = len(set_data.get("tracks", []))

            # Import into graph if available
            if self._graph and set_data:
                import json
                import tempfile

                with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                    json.dump(set_data, f)
                    f.flush()
                    result = await import_file(f.name, self._graph)
                    report.transitions_created = result.transitions_created
                    if result.errors:
                        report.error = "; ".join(result.errors)

            report.success = True

        except Exception as exc:
            logger.exception("Learn from URL failed: %s", url)
            report.error = str(exc)

        return report
