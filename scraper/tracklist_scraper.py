"""1001tracklists.com scraper — Playwright-based tracklist discovery and parsing."""

from __future__ import annotations

import json
import logging
import random
import re
import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from playwright.async_api import Page, async_playwright

logger = logging.getLogger(__name__)

QUEUE_PATH = Path("scraper/queue.json")
OUTPUT_DIR = Path("scraper/output")
BASE_URL = "https://www.1001tracklists.com"

MIN_DELAY = 2.0
MAX_DELAY = 5.0


# ---------------------------------------------------------------------------
# Queue management — resume support
# ---------------------------------------------------------------------------


@dataclass
class QueueEntry:
    url: str
    status: str = "pending"  # pending | done | error
    error: str | None = None


def load_queue() -> list[QueueEntry]:
    if QUEUE_PATH.exists():
        raw = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        return [QueueEntry(**e) for e in raw]
    return []


def save_queue(queue: list[QueueEntry]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = [{"url": e.url, "status": e.status, "error": e.error} for e in queue]
    QUEUE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


async def polite_delay() -> None:
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


# ---------------------------------------------------------------------------
# Sanitize filenames
# ---------------------------------------------------------------------------


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", name).strip("_")[:100]


# ---------------------------------------------------------------------------
# Discovery — collect tracklist URLs from genre pages
# ---------------------------------------------------------------------------


async def discover_sets(
    page: Page,
    genre: str = "tech-house",
    max_sets: int = 100,
) -> list[str]:
    """Browse genre listing pages and collect tracklist URLs."""
    urls: list[str] = []
    page_num = 1
    genre_slug = genre.lower().replace(" ", "-")

    while len(urls) < max_sets:
        listing_url = f"{BASE_URL}/genre/{genre_slug}/index{page_num}.html" if page_num > 1 else f"{BASE_URL}/genre/{genre_slug}/index.html"
        logger.info("Discovering page %d: %s", page_num, listing_url)

        try:
            await page.goto(listing_url, wait_until="domcontentloaded", timeout=30000)
        except Exception as exc:
            logger.warning("Failed to load listing page %d: %s", page_num, exc)
            break

        # Extract tracklist links — they match /tracklist/ pattern
        links = await page.eval_on_selector_all(
            'a[href*="/tracklist/"]',
            "els => els.map(e => e.href)",
        )

        new_urls = []
        for link in links:
            if "/tracklist/" in link and link not in urls and link not in new_urls:
                new_urls.append(link)

        if not new_urls:
            logger.info("No more tracklists found on page %d", page_num)
            break

        urls.extend(new_urls)
        logger.info("Found %d new URLs (total: %d)", len(new_urls), len(urls))

        page_num += 1
        await polite_delay()

    return urls[:max_sets]


# ---------------------------------------------------------------------------
# Per-set parsing
# ---------------------------------------------------------------------------


async def parse_tracklist(page: Page, url: str) -> dict | None:
    """Parse a single tracklist page into a SetImport-compatible dict."""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as exc:
        logger.warning("Failed to load tracklist %s: %s", url, exc)
        return None

    await polite_delay()

    try:
        result = await page.evaluate("""() => {
            // DJ name
            const djEl = document.querySelector('.dj_name a, [itemprop="name"]');
            const djName = djEl ? djEl.textContent.trim() : null;

            // Event info
            const metaEls = document.querySelectorAll('.meta_data span, .tl_info span');
            let event = null, date = null, venue = null;
            metaEls.forEach(el => {
                const text = el.textContent.trim();
                if (text.match(/\\d{4}-\\d{2}-\\d{2}/)) date = text;
                else if (el.querySelector('a[href*="/event/"]')) event = text;
                else if (el.querySelector('a[href*="/venue/"]')) venue = text;
            });

            // Title/event from header
            const headerEl = document.querySelector('h1, .tlInfo');
            const headerText = headerEl ? headerEl.textContent.trim() : '';
            if (!event && headerText) event = headerText;

            // Tracks
            const trackEls = document.querySelectorAll('.tlpItem, .track_value, [itemtype*="MusicRecording"]');
            const tracks = [];
            trackEls.forEach(el => {
                const titleEl = el.querySelector('.trackFormat .value, [itemprop="name"], .trackValue');
                const artistEl = el.querySelector('.trackFormat .value:first-child, [itemprop="byArtist"], .artistValue');
                const labelEl = el.querySelector('.labelValue a, [itemprop="publisher"]');
                const bpmEl = el.querySelector('.bpmValue');

                let fullText = el.textContent || '';
                // Try to parse "Artist - Title (Remix)" format
                let artist = artistEl ? artistEl.textContent.trim() : null;
                let title = titleEl ? titleEl.textContent.trim() : null;
                let remix = null;
                let label = labelEl ? labelEl.textContent.trim() : null;
                let bpm = bpmEl ? parseFloat(bpmEl.textContent) : null;

                // Parse combined "Artist - Title" if separate elements not found
                if ((!artist || !title) && fullText.includes(' - ')) {
                    const parts = fullText.split(' - ');
                    if (parts.length >= 2) {
                        artist = artist || parts[0].trim();
                        let rest = parts.slice(1).join(' - ').trim();
                        // Extract remix from parentheses
                        const remixMatch = rest.match(/\\(([^)]+(?:remix|mix|edit|version|dub)[^)]*)\\)/i);
                        if (remixMatch) {
                            remix = remixMatch[1].trim();
                            rest = rest.replace(remixMatch[0], '').trim();
                        }
                        title = title || rest;
                    }
                }

                if (artist && title) {
                    const track = { title, artist };
                    if (remix) track.remix = remix;
                    if (label) track.label = label;
                    if (bpm && !isNaN(bpm)) track.bpm = bpm;
                    track.genre = ['tech house'];
                    tracks.push(track);
                }
            });

            return { djName, event, date, venue, tracks };
        }""")

        if not result or not result.get("djName") or not result.get("tracks"):
            logger.warning("Could not parse tracklist from %s", url)
            return None

        return {
            "dj": result["djName"],
            "event": result.get("event"),
            "date": result.get("date"),
            "venue": result.get("venue"),
            "source_url": url,
            "tracks": result["tracks"],
        }

    except Exception as exc:
        logger.warning("Error parsing tracklist %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Per-DJ parsing
# ---------------------------------------------------------------------------


async def parse_dj_profile(page: Page, dj_name: str) -> dict | None:
    """Visit a DJ profile page and extract genres and set count."""
    slug = dj_name.lower().replace(" ", "").replace("&", "and")
    profile_url = f"{BASE_URL}/dj/{slug}/index.html"

    try:
        await page.goto(profile_url, wait_until="domcontentloaded", timeout=30000)
    except Exception as exc:
        logger.warning("Failed to load DJ profile %s: %s", profile_url, exc)
        return None

    await polite_delay()

    try:
        result = await page.evaluate("""() => {
            const genreEls = document.querySelectorAll('.genre_nav a, .genres a');
            const genres = Array.from(genreEls).map(e => e.textContent.trim()).filter(Boolean);

            const countEl = document.querySelector('.tl_count, .setCount');
            let setCount = 0;
            if (countEl) {
                const match = countEl.textContent.match(/(\\d+)/);
                if (match) setCount = parseInt(match[1]);
            }

            return { genres, setCount };
        }""")

        return {
            "name": dj_name,
            "genres": result.get("genres", []),
            "profile_url": profile_url,
            "set_count": result.get("setCount", 0),
        }
    except Exception as exc:
        logger.warning("Error parsing DJ profile %s: %s", dj_name, exc)
        return None


# ---------------------------------------------------------------------------
# Main scraper orchestrator
# ---------------------------------------------------------------------------


async def scrape(
    genre: str = "tech house",
    max_sets: int = 100,
    output_dir: str | None = None,
) -> dict:
    """Run the full scraping pipeline: discover, parse, save."""
    out = Path(output_dir) if output_dir else OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    stats = {"discovered": 0, "parsed": 0, "errors": 0, "dj_profiles": 0}
    seen_djs: dict[str, dict] = {}

    # Load or initialize queue
    queue = load_queue()
    existing_urls = {e.url for e in queue}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()

        # Set a realistic user-agent
        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })

        # Discovery phase
        logger.info("Starting discovery for genre: %s (max %d sets)", genre, max_sets)
        discovered = await discover_sets(page, genre, max_sets)
        stats["discovered"] = len(discovered)

        for url in discovered:
            if url not in existing_urls:
                queue.append(QueueEntry(url=url))
        save_queue(queue)

        # Parse phase
        for entry in queue:
            if entry.status != "pending":
                continue

            logger.info("Parsing: %s", entry.url)
            set_data = await parse_tracklist(page, entry.url)

            if set_data is None:
                entry.status = "error"
                entry.error = "parse_failed"
                stats["errors"] += 1
                save_queue(queue)
                continue

            # Parse DJ profile if not seen
            dj_name = set_data["dj"]
            if dj_name not in seen_djs:
                dj_data = await parse_dj_profile(page, dj_name)
                if dj_data:
                    seen_djs[dj_name] = dj_data
                    set_data["dj"] = dj_data
                    stats["dj_profiles"] += 1

            elif dj_name in seen_djs:
                set_data["dj"] = seen_djs[dj_name]

            # Save output
            event_name = sanitize_filename(set_data.get("event") or "unknown")
            date_str = sanitize_filename(set_data.get("date") or "nodate")
            dj_slug = sanitize_filename(dj_name)
            filename = f"{dj_slug}_{event_name}_{date_str}.json"

            output_path = out / filename
            output_path.write_text(
                json.dumps(set_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("Saved: %s (%d tracks)", filename, len(set_data.get("tracks", [])))

            entry.status = "done"
            stats["parsed"] += 1
            save_queue(queue)

        await browser.close()

    logger.info(
        "Scraping complete: %d discovered, %d parsed, %d errors, %d DJ profiles",
        stats["discovered"], stats["parsed"], stats["errors"], stats["dj_profiles"],
    )
    return stats
