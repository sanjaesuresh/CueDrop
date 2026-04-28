"""yt-dlp wrapper for downloading audio from DJ set URLs (YouTube, SoundCloud, etc.)."""

from __future__ import annotations

import asyncio
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of downloading a DJ set."""

    url: str
    file_path: str = ""
    title: str = ""
    duration_s: float = 0.0
    uploader: str = ""
    success: bool = False
    error: str | None = None


@dataclass
class SetMetadata:
    """Metadata extracted from video/audio page."""

    title: str = ""
    uploader: str = ""
    duration_s: float = 0.0
    description: str = ""
    view_count: int = 0
    upload_date: str = ""  # YYYYMMDD


async def extract_metadata(url: str) -> SetMetadata:
    """Extract metadata from a URL without downloading.

    Uses yt-dlp's info extraction (no download).
    """
    meta = SetMetadata()
    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)

        info = await asyncio.get_event_loop().run_in_executor(None, _extract)

        if info:
            meta.title = info.get("title", "")
            meta.uploader = info.get("uploader", "") or info.get("channel", "")
            meta.duration_s = float(info.get("duration", 0) or 0)
            meta.description = info.get("description", "") or ""
            meta.view_count = int(info.get("view_count", 0) or 0)
            meta.upload_date = info.get("upload_date", "") or ""

    except Exception as exc:
        logger.warning("Metadata extraction failed for %s: %s", url, exc)

    return meta


async def download_audio(
    url: str,
    output_dir: str | None = None,
    format_preference: str = "bestaudio/best",
) -> DownloadResult:
    """Download audio from a URL using yt-dlp.

    Args:
        url: Video/audio URL (YouTube, SoundCloud, etc.).
        output_dir: Directory for output file. Uses temp dir if None.
        format_preference: yt-dlp format string.

    Returns:
        DownloadResult with file path and metadata.
    """
    result = DownloadResult(url=url)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="cuedrop_yt_")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    try:
        import yt_dlp

        ydl_opts = {
            "format": format_preference,
            "outtmpl": str(out_path / "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }],
            "quiet": True,
            "no_warnings": True,
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await asyncio.get_event_loop().run_in_executor(None, _download)

        if info:
            result.title = info.get("title", "")
            result.uploader = info.get("uploader", "") or info.get("channel", "")
            result.duration_s = float(info.get("duration", 0) or 0)

            # Find the downloaded file
            for f in out_path.iterdir():
                if f.suffix in (".wav", ".mp3", ".m4a", ".opus", ".webm"):
                    result.file_path = str(f)
                    break

            result.success = bool(result.file_path)
            if not result.success:
                result.error = "Download completed but audio file not found"

    except Exception as exc:
        logger.error("Download failed for %s: %s", url, exc)
        result.error = str(exc)

    return result


@dataclass
class TimestampedTrack:
    """A track identified at a specific timestamp in a set."""

    title: str
    artist: str
    timestamp_s: float  # seconds into the set
    confidence: float = 1.0  # 0–1
    source: str = "description"  # description, fingerprint, manual


def parse_tracklist_from_description(description: str) -> list[TimestampedTrack]:
    """Extract tracklist from video description timestamps.

    Looks for common patterns like:
    - 00:00 Artist - Title
    - 0:00:00 Artist - Title
    - [00:00] Artist - Title
    """
    import re

    tracks: list[TimestampedTrack] = []

    # Pattern: various timestamp formats followed by track info
    patterns = [
        # HH:MM:SS or H:MM:SS
        r"(\d{1,2}):(\d{2}):(\d{2})\s*[-–]?\s*(.+)",
        # MM:SS
        r"(\d{1,3}):(\d{2})\s*[-–]?\s*(.+)",
        # [HH:MM:SS] or [MM:SS]
        r"\[(\d{1,2}):(\d{2}):(\d{2})\]\s*[-–]?\s*(.+)",
        r"\[(\d{1,3}):(\d{2})\]\s*[-–]?\s*(.+)",
    ]

    for line in description.split("\n"):
        line = line.strip()
        if not line:
            continue

        for pattern in patterns:
            m = re.match(pattern, line)
            if m:
                groups = m.groups()
                if len(groups) == 4:
                    # HH:MM:SS format
                    hours, mins, secs, track_info = groups
                    timestamp_s = int(hours) * 3600 + int(mins) * 60 + int(secs)
                elif len(groups) == 3:
                    # MM:SS format
                    mins, secs, track_info = groups
                    timestamp_s = int(mins) * 60 + int(secs)
                else:
                    continue

                track_info = track_info.strip()
                # Try to split "Artist - Title"
                if " - " in track_info:
                    parts = track_info.split(" - ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                elif " – " in track_info:
                    parts = track_info.split(" – ", 1)
                    artist = parts[0].strip()
                    title = parts[1].strip()
                else:
                    artist = ""
                    title = track_info

                # Clean up common suffixes
                for suffix in ["(Official Audio)", "(Official Video)", "(Lyrics)"]:
                    title = title.replace(suffix, "").strip()

                tracks.append(TimestampedTrack(
                    title=title,
                    artist=artist,
                    timestamp_s=float(timestamp_s),
                    source="description",
                ))
                break  # matched, move to next line

    return tracks
