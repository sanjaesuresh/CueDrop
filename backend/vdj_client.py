"""VirtualDJ HTTP API wrapper."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass
class DeckStatus:
    deck: int = 1
    artist: str = ""
    title: str = ""
    time_ms: int = 0
    bpm: float = 0.0
    is_playing: bool = False


class VDJClientProtocol(Protocol):
    async def load_track(self, deck: int, uri: str) -> bool: ...
    async def play(self, deck: int) -> None: ...
    async def pause(self, deck: int) -> None: ...
    async def stop(self, deck: int) -> None: ...
    async def crossfade(self, pct: float) -> None: ...
    async def eq(self, deck: int, band: str, pct: float) -> None: ...
    async def sync(self, deck: int) -> None: ...
    async def set_bpm(self, deck: int, bpm: float) -> None: ...
    async def get_status(self) -> list[DeckStatus]: ...
    async def execute(self, vdjscript: str) -> str: ...
    async def query(self, vdjscript: str) -> str: ...
    async def close(self) -> None: ...


class VDJClient:
    """Async HTTP client for VirtualDJ's NetworkControlPlugin."""

    def __init__(self, host: str = "http://127.0.0.1:80", auth_token: str = "") -> None:
        self._host = host.rstrip("/")
        self._auth_token = auth_token
        self._client = httpx.AsyncClient(timeout=5.0)

    async def _send(self, endpoint: str, params: dict | None = None) -> str:
        headers = {}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        resp = await self._client.get(f"{self._host}/{endpoint}", params=params or {}, headers=headers)
        resp.raise_for_status()
        return resp.text

    async def execute(self, vdjscript: str) -> str:
        return await self._send("execute", {"script": vdjscript})

    async def query(self, vdjscript: str) -> str:
        return await self._send("query", {"script": vdjscript})

    async def load_track(self, deck: int, uri: str) -> bool:
        try:
            await self.execute(f"deck {deck} load '{uri}'")
            return True
        except Exception:
            logger.exception("Failed to load track on deck %d", deck)
            return False

    async def play(self, deck: int) -> None:
        await self.execute(f"deck {deck} play")

    async def pause(self, deck: int) -> None:
        await self.execute(f"deck {deck} pause")

    async def stop(self, deck: int) -> None:
        await self.execute(f"deck {deck} stop")

    async def crossfade(self, pct: float) -> None:
        await self.execute(f"crossfader {pct}%")

    async def eq(self, deck: int, band: str, pct: float) -> None:
        await self.execute(f"deck {deck} eq_{band} {pct}%")

    async def sync(self, deck: int) -> None:
        await self.execute(f"deck {deck} sync")

    async def set_bpm(self, deck: int, bpm: float) -> None:
        await self.execute(f"deck {deck} bpm {bpm}")

    async def get_status(self) -> list[DeckStatus]:
        statuses = []
        for deck in (1, 2):
            try:
                artist = await self.query(f"deck {deck} get_artist")
                title = await self.query(f"deck {deck} get_title")
                time_ms = int(await self.query(f"deck {deck} get_time") or "0")
                bpm = float(await self.query(f"deck {deck} get_bpm") or "0")
                playing = (await self.query(f"deck {deck} get_isplaying")).strip() == "1"
                statuses.append(DeckStatus(
                    deck=deck, artist=artist.strip(), title=title.strip(),
                    time_ms=time_ms, bpm=bpm, is_playing=playing,
                ))
            except Exception:
                logger.warning("Could not query deck %d status", deck)
                statuses.append(DeckStatus(deck=deck))
        return statuses

    async def close(self) -> None:
        await self._client.aclose()


class MockVDJClient:
    """In-memory fake for development without VDJ running."""

    def __init__(self) -> None:
        self.decks: dict[int, DeckStatus] = {
            1: DeckStatus(deck=1),
            2: DeckStatus(deck=2),
        }
        self.crossfader: float = 50.0
        self.commands: list[str] = []

    async def load_track(self, deck: int, uri: str) -> bool:
        self.commands.append(f"load deck={deck} uri={uri}")
        d = self.decks.setdefault(deck, DeckStatus(deck=deck))
        # Parse artist - title from URI filename
        name = uri.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if " - " in name:
            d.artist, d.title = name.split(" - ", 1)
        else:
            d.title = name
            d.artist = ""
        d.time_ms = 0
        d.bpm = 128.0
        return True

    async def play(self, deck: int) -> None:
        self.commands.append(f"play deck={deck}")
        self.decks[deck].is_playing = True

    async def pause(self, deck: int) -> None:
        self.commands.append(f"pause deck={deck}")
        self.decks[deck].is_playing = False

    async def stop(self, deck: int) -> None:
        self.commands.append(f"stop deck={deck}")
        self.decks[deck].is_playing = False
        self.decks[deck].time_ms = 0

    async def crossfade(self, pct: float) -> None:
        self.commands.append(f"crossfade {pct}%")
        self.crossfader = pct

    async def eq(self, deck: int, band: str, pct: float) -> None:
        self.commands.append(f"eq deck={deck} band={band} {pct}%")

    async def sync(self, deck: int) -> None:
        self.commands.append(f"sync deck={deck}")

    async def set_bpm(self, deck: int, bpm: float) -> None:
        self.commands.append(f"bpm deck={deck} {bpm}")
        self.decks[deck].bpm = bpm

    async def get_status(self) -> list[DeckStatus]:
        return [self.decks[1], self.decks[2]]

    async def execute(self, vdjscript: str) -> str:
        self.commands.append(f"exec: {vdjscript}")
        return "ok"

    async def query(self, vdjscript: str) -> str:
        self.commands.append(f"query: {vdjscript}")
        return ""

    async def close(self) -> None:
        self.commands.append("close")
