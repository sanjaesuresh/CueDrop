"""Music resolution — search and find playable sources for tracks."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class SourceType(str, Enum):
    LOCAL = "local"
    BEATPORT_EDIT = "beatport_edit"
    BEATPORT = "beatport"
    TIDAL = "tidal"
    NOT_FOUND = "not_found"


@dataclass
class PlayableSource:
    """A resolved playable source for a track."""

    source_type: SourceType
    uri: str
    title: str
    artist: str
    bpm: float | None = None
    is_dj_edit: bool = False


@dataclass
class SearchResult:
    """A search result from Spotify."""

    spotify_id: str
    title: str
    artist: str
    album: str = ""
    duration_ms: int = 0
    preview_url: str | None = None


class MusicResolver:
    """Search Spotify for tracks, resolve to a playable source."""

    def __init__(
        self,
        local_library_path: str | None = None,
        spotify_client_id: str = "",
        spotify_client_secret: str = "",
    ) -> None:
        self._local_path = Path(local_library_path) if local_library_path else None
        self._spotify_client_id = spotify_client_id
        self._spotify_client_secret = spotify_client_secret
        self._spotify_token: str | None = None
        self._http = httpx.AsyncClient(timeout=10.0)

    async def _get_spotify_token(self) -> str | None:
        """Get or refresh Spotify client credentials token."""
        if self._spotify_token:
            return self._spotify_token
        if not self._spotify_client_id or not self._spotify_client_secret:
            return None
        try:
            resp = await self._http.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                auth=(self._spotify_client_id, self._spotify_client_secret),
            )
            resp.raise_for_status()
            self._spotify_token = resp.json()["access_token"]
            return self._spotify_token
        except Exception as exc:
            logger.warning("Failed to get Spotify token: %s", exc)
            return None

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search Spotify for tracks."""
        token = await self._get_spotify_token()
        if not token:
            logger.info("No Spotify credentials — returning empty search")
            return []

        try:
            resp = await self._http.get(
                "https://api.spotify.com/v1/search",
                params={"q": query, "type": "track", "limit": limit},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("tracks", {}).get("items", []):
                artists = ", ".join(a["name"] for a in item.get("artists", []))
                results.append(SearchResult(
                    spotify_id=item["id"],
                    title=item["name"],
                    artist=artists,
                    album=item.get("album", {}).get("name", ""),
                    duration_ms=item.get("duration_ms", 0),
                    preview_url=item.get("preview_url"),
                ))
            return results
        except Exception as exc:
            logger.warning("Spotify search failed: %s", exc)
            return []

    def _search_local(self, artist: str, title: str) -> PlayableSource | None:
        """Search local library for a matching file."""
        if not self._local_path or not self._local_path.exists():
            return None

        # Search for common patterns
        patterns = [
            f"*{artist}*{title}*",
            f"*{title}*{artist}*",
            f"*{artist}*-*{title}*",
        ]
        for pattern in patterns:
            for ext in ("*.mp3", "*.wav", "*.flac", "*.aiff", "*.m4a"):
                for match in self._local_path.rglob(f"{pattern}{ext[1:]}"):
                    return PlayableSource(
                        source_type=SourceType.LOCAL,
                        uri=str(match),
                        title=title,
                        artist=artist,
                    )
        return None

    async def resolve(self, artist: str, title: str) -> PlayableSource:
        """Find a playable source for a track.

        Resolution priority: local file → Beatport DJ edit → Beatport original → Tidal → not found.
        Beatport and Tidal integration are stubs for Phase 3.
        """
        # 1. Local file
        local = self._search_local(artist, title)
        if local:
            logger.info("Resolved locally: %s - %s", artist, title)
            return local

        # 2. Beatport DJ edit (stub)
        # 3. Beatport original (stub)
        # 4. Tidal (stub)

        logger.info("Could not resolve: %s - %s", artist, title)
        return PlayableSource(
            source_type=SourceType.NOT_FOUND,
            uri="",
            title=title,
            artist=artist,
        )

    async def close(self) -> None:
        await self._http.aclose()
