"""Tests for VDJ client — MockVDJClient (no network)."""

from __future__ import annotations

import pytest

from backend.vdj_client import DeckStatus, MockVDJClient


@pytest.fixture
def mock_vdj():
    return MockVDJClient()


# ---------------------------------------------------------------------------
# DeckStatus
# ---------------------------------------------------------------------------


def test_deck_status_defaults():
    ds = DeckStatus()
    assert ds.deck == 1
    assert ds.artist == ""
    assert ds.title == ""
    assert ds.bpm == 0.0
    assert ds.is_playing is False


# ---------------------------------------------------------------------------
# MockVDJClient — load_track
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_track(mock_vdj):
    result = await mock_vdj.load_track(1, "/music/Fisher - Losing It.mp3")
    assert result is True
    assert mock_vdj.decks[1].artist == "Fisher"
    assert mock_vdj.decks[1].title == "Losing It"
    assert mock_vdj.decks[1].time_ms == 0


@pytest.mark.asyncio
async def test_load_track_no_separator(mock_vdj):
    result = await mock_vdj.load_track(2, "/music/some_track.wav")
    assert result is True
    assert mock_vdj.decks[2].title == "some_track"
    assert mock_vdj.decks[2].artist == ""


# ---------------------------------------------------------------------------
# MockVDJClient — transport
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_play(mock_vdj):
    await mock_vdj.play(1)
    assert mock_vdj.decks[1].is_playing is True


@pytest.mark.asyncio
async def test_pause(mock_vdj):
    await mock_vdj.play(1)
    await mock_vdj.pause(1)
    assert mock_vdj.decks[1].is_playing is False


@pytest.mark.asyncio
async def test_stop_resets_time(mock_vdj):
    mock_vdj.decks[1].time_ms = 5000
    mock_vdj.decks[1].is_playing = True
    await mock_vdj.stop(1)
    assert mock_vdj.decks[1].is_playing is False
    assert mock_vdj.decks[1].time_ms == 0


# ---------------------------------------------------------------------------
# MockVDJClient — mixer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crossfade(mock_vdj):
    await mock_vdj.crossfade(75.0)
    assert mock_vdj.crossfader == 75.0


@pytest.mark.asyncio
async def test_eq(mock_vdj):
    await mock_vdj.eq(1, "low", 50.0)
    assert "eq deck=1 band=low 50.0%" in mock_vdj.commands


@pytest.mark.asyncio
async def test_sync(mock_vdj):
    await mock_vdj.sync(1)
    assert "sync deck=1" in mock_vdj.commands


@pytest.mark.asyncio
async def test_set_bpm(mock_vdj):
    await mock_vdj.set_bpm(1, 126.0)
    assert mock_vdj.decks[1].bpm == 126.0


# ---------------------------------------------------------------------------
# MockVDJClient — status & scripting
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status(mock_vdj):
    await mock_vdj.load_track(1, "/music/Fisher - Losing It.mp3")
    await mock_vdj.play(1)
    statuses = await mock_vdj.get_status()
    assert len(statuses) == 2
    assert statuses[0].is_playing is True
    assert statuses[1].is_playing is False


@pytest.mark.asyncio
async def test_execute(mock_vdj):
    result = await mock_vdj.execute("deck 1 play")
    assert result == "ok"
    assert "exec: deck 1 play" in mock_vdj.commands


@pytest.mark.asyncio
async def test_query(mock_vdj):
    result = await mock_vdj.query("deck 1 get_bpm")
    assert result == ""
    assert "query: deck 1 get_bpm" in mock_vdj.commands


@pytest.mark.asyncio
async def test_close(mock_vdj):
    await mock_vdj.close()
    assert "close" in mock_vdj.commands


# ---------------------------------------------------------------------------
# Command history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_history(mock_vdj):
    await mock_vdj.load_track(1, "/music/track.mp3")
    await mock_vdj.play(1)
    await mock_vdj.crossfade(100.0)
    assert len(mock_vdj.commands) == 3
