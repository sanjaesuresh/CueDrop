"""Tests for MusicResolver — local resolution, no network calls."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from backend.music_resolver import MusicResolver, PlayableSource, SearchResult, SourceType


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


def test_search_result():
    sr = SearchResult(spotify_id="abc", title="Cola", artist="CamelPhat", duration_ms=360000)
    assert sr.spotify_id == "abc"
    assert sr.title == "Cola"


# ---------------------------------------------------------------------------
# PlayableSource
# ---------------------------------------------------------------------------


def test_playable_source():
    ps = PlayableSource(source_type=SourceType.LOCAL, uri="/music/track.mp3", title="T", artist="A")
    assert ps.source_type == SourceType.LOCAL
    assert ps.is_dj_edit is False


# ---------------------------------------------------------------------------
# Local resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_local_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a matching file
        p = Path(tmpdir) / "Fisher - Losing It.mp3"
        p.write_text("fake audio")

        resolver = MusicResolver(local_library_path=tmpdir)
        result = await resolver.resolve("Fisher", "Losing It")
        await resolver.close()

    assert result.source_type == SourceType.LOCAL
    assert "Losing It" in result.uri


@pytest.mark.asyncio
async def test_resolve_local_not_found():
    with tempfile.TemporaryDirectory() as tmpdir:
        resolver = MusicResolver(local_library_path=tmpdir)
        result = await resolver.resolve("Nonexistent", "Track")
        await resolver.close()

    assert result.source_type == SourceType.NOT_FOUND


@pytest.mark.asyncio
async def test_resolve_no_local_path():
    resolver = MusicResolver()
    result = await resolver.resolve("Fisher", "Losing It")
    await resolver.close()
    assert result.source_type == SourceType.NOT_FOUND


# ---------------------------------------------------------------------------
# Search without credentials returns empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_no_credentials():
    resolver = MusicResolver()
    results = await resolver.search("Fisher Losing It")
    await resolver.close()
    assert results == []


# ---------------------------------------------------------------------------
# SourceType enum
# ---------------------------------------------------------------------------


def test_source_types():
    assert SourceType.LOCAL == "local"
    assert SourceType.BEATPORT_EDIT == "beatport_edit"
    assert SourceType.NOT_FOUND == "not_found"
    assert len(SourceType) == 5
