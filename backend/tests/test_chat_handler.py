"""Tests for ChatHandler — fallback parsing (no API calls)."""

from __future__ import annotations

import pytest

from backend.chat_handler import ChatHandler, Intent
from backend.models import SetState


@pytest.fixture
def handler():
    """ChatHandler with no API key — uses fallback parsing."""
    return ChatHandler(api_key="")


# ---------------------------------------------------------------------------
# Fallback parsing — skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skip(handler):
    result = await handler.process_message("skip")
    assert result.type == "skip"


@pytest.mark.asyncio
async def test_next(handler):
    result = await handler.process_message("next track")
    assert result.type == "skip"


# ---------------------------------------------------------------------------
# Fallback parsing — track request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_track_request_play(handler):
    result = await handler.process_message("play Losing It by Fisher")
    assert result.type == "track_request"


@pytest.mark.asyncio
async def test_track_request_drop(handler):
    result = await handler.process_message("drop Cola")
    assert result.type == "track_request"


@pytest.mark.asyncio
async def test_track_request_queue(handler):
    result = await handler.process_message("queue up some CamelPhat")
    assert result.type == "track_request"


# ---------------------------------------------------------------------------
# Fallback parsing — energy shift
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_energy_up(handler):
    result = await handler.process_message("more energy please")
    assert result.type == "energy_shift"
    assert result.data["direction"] == "up"


@pytest.mark.asyncio
async def test_energy_down(handler):
    result = await handler.process_message("chill out a bit")
    assert result.type == "energy_shift"
    assert result.data["direction"] == "down"


@pytest.mark.asyncio
async def test_turn_up(handler):
    result = await handler.process_message("turn up!")
    assert result.type == "energy_shift"


# ---------------------------------------------------------------------------
# Fallback parsing — vibe request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_vibe_darker(handler):
    result = await handler.process_message("go darker")
    assert result.type == "vibe_request"
    assert result.data["vibe"] == "darker"


@pytest.mark.asyncio
async def test_vibe_deeper(handler):
    result = await handler.process_message("make it deeper")
    assert result.type == "vibe_request"
    assert result.data["vibe"] == "deeper"


# ---------------------------------------------------------------------------
# Fallback parsing — query
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_what(handler):
    result = await handler.process_message("what's playing?")
    assert result.type == "query"


@pytest.mark.asyncio
async def test_query_stats(handler):
    result = await handler.process_message("how many tracks in queue?")
    assert result.type == "query"


# ---------------------------------------------------------------------------
# Fallback parsing — unknown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_defaults_to_query(handler):
    result = await handler.process_message("asdfghjkl")
    assert result.type == "query"
    assert result.response  # should have a helpful message


# ---------------------------------------------------------------------------
# With set state (still fallback, but tests the code path)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_with_set_state(handler):
    state = SetState(current_bpm=128.0, current_key="8A", genres=["tech house"])
    result = await handler.process_message("skip", state)
    assert result.type == "skip"


# ---------------------------------------------------------------------------
# Intent dataclass
# ---------------------------------------------------------------------------


def test_intent_creation():
    i = Intent(type="skip", data={}, response="Done.")
    assert i.type == "skip"
    assert i.data == {}
    assert i.response == "Done."
