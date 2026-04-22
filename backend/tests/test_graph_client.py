"""Tests for GraphClient — mocked Neo4j driver (no live DB required)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.graph_client import GraphClient
from backend.models import DJModel, SetModel, TrackModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_driver() -> tuple[MagicMock, AsyncMock]:
    """Return (driver_mock, session_mock) wired together."""
    session = AsyncMock()
    # session.run returns an async result whose .single() we can configure
    run_result = AsyncMock()
    session.run.return_value = run_result

    driver = MagicMock()
    # AsyncContextManager for session()
    driver.session.return_value.__aenter__ = AsyncMock(return_value=session)
    driver.session.return_value.__aexit__ = AsyncMock(return_value=False)
    driver.close = AsyncMock()

    return driver, session, run_result


@pytest.fixture
def client_and_mocks():
    """Patch AsyncGraphDatabase.driver and return (client, session_mock, run_result)."""
    driver, session, run_result = _make_mock_driver()
    with patch(
        "backend.graph_client.AsyncGraphDatabase.driver", return_value=driver
    ):
        client = GraphClient()
    # Expose internals for assertions
    return client, session, run_result, driver


# ---------------------------------------------------------------------------
# ensure_schema
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_schema_runs_all_statements(client_and_mocks):
    client, session, *_ = client_and_mocks
    await client.ensure_schema()

    # Should have executed exactly 7 Cypher statements
    assert session.run.call_count == 7

    calls = [c.args[0] for c in session.run.call_args_list]
    assert any("track_id_unique" in c for c in calls)
    assert any("dj_name_unique" in c for c in calls)
    assert any("set_id_unique" in c for c in calls)
    assert any("track_artist_idx" in c for c in calls)
    assert any("track_bpm_idx" in c for c in calls)
    assert any("track_genre_idx" in c for c in calls)
    assert any("track_search" in c for c in calls)


# ---------------------------------------------------------------------------
# upsert_track
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_track_returns_track_id(client_and_mocks):
    client, session, run_result, _ = client_and_mocks

    record = {"track_id": "artist::title::original"}
    run_result.single.return_value = record

    track = TrackModel(title="Title", artist="Artist")
    result = await client.upsert_track(track)

    assert result == "artist::title::original"
    session.run.assert_called_once()
    query_arg = session.run.call_args.args[0]
    assert "MERGE (t:Track {track_id: $track_id})" in query_arg
    assert "coalesce($bpm, t.bpm)" in query_arg

    # Required fields (title, artist) should be SET directly, not via coalesce
    assert "t.title = $title" in query_arg
    assert "t.artist = $artist" in query_arg


@pytest.mark.asyncio
async def test_upsert_track_passes_correct_params(client_and_mocks):
    client, session, run_result, _ = client_and_mocks
    run_result.single.return_value = {"track_id": "dj::track::original"}

    track = TrackModel(title="Track", artist="DJ", bpm=128.0, key="Am")
    await client.upsert_track(track)

    params = session.run.call_args.args[1]
    assert params["title"] == "Track"
    assert params["artist"] == "DJ"
    assert params["bpm"] == 128.0
    assert params["key"] == "Am"


@pytest.mark.asyncio
async def test_upsert_track_nullifies_empty_genre(client_and_mocks):
    client, session, run_result, _ = client_and_mocks
    run_result.single.return_value = {"track_id": "a::b::original"}

    track = TrackModel(title="b", artist="a", genre=[])
    await client.upsert_track(track)

    params = session.run.call_args.args[1]
    assert params["genre"] is None


# ---------------------------------------------------------------------------
# upsert_transition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_transition_cypher(client_and_mocks):
    client, session, *_ = client_and_mocks

    await client.upsert_transition("id_a", "id_b", "tracklist_xyz")

    session.run.assert_called_once()
    query = session.run.call_args.args[0]
    params = session.run.call_args.args[1]

    assert "MERGE (a)-[r:TRANSITIONS_TO]->(b)" in query
    assert "r.frequency = coalesce(r.frequency, 0) + 1" in query
    assert params == {"from_id": "id_a", "to_id": "id_b", "source": "tracklist_xyz"}


# ---------------------------------------------------------------------------
# upsert_dj
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_dj(client_and_mocks):
    client, session, *_ = client_and_mocks
    dj = DJModel(name="Skrillex", genres=["dubstep"])
    await client.upsert_dj(dj)

    session.run.assert_called_once()
    query = session.run.call_args.args[0]
    params = session.run.call_args.args[1]

    assert "MERGE (d:DJ {name: $name})" in query
    assert params["name"] == "Skrillex"
    assert params["genres"] == ["dubstep"]


@pytest.mark.asyncio
async def test_upsert_dj_empty_genres_nullified(client_and_mocks):
    client, session, *_ = client_and_mocks
    dj = DJModel(name="Tiesto")
    await client.upsert_dj(dj)

    params = session.run.call_args.args[1]
    assert params["genres"] is None


# ---------------------------------------------------------------------------
# upsert_set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_set_creates_graph(client_and_mocks):
    client, session, run_result, _ = client_and_mocks

    # upsert_track returns track_id from the record
    run_result.single.return_value = {"track_id": "mock_id"}

    tracks = [
        TrackModel(title="A", artist="X"),
        TrackModel(title="B", artist="Y"),
        TrackModel(title="C", artist="Z"),
    ]
    set_data = SetModel(
        set_id="set_001",
        dj_name="DJ Test",
        event="Festival",
        source_url="https://example.com",
    )

    await client.upsert_set(set_data, tracks)

    all_queries = [c.args[0] for c in session.run.call_args_list]

    # 3 track upserts + 1 DJ upsert + 1 set creation + 3 CONTAINS + 2 transitions = 10
    assert session.run.call_count == 10

    # Verify set creation query links DJ
    set_queries = [q for q in all_queries if "PLAYED_SET" in q]
    assert len(set_queries) == 1

    # Verify CONTAINS edges
    contains_queries = [q for q in all_queries if "CONTAINS" in q]
    assert len(contains_queries) == 3

    # Verify transitions
    transition_queries = [q for q in all_queries if "TRANSITIONS_TO" in q]
    assert len(transition_queries) == 2


# ---------------------------------------------------------------------------
# get_track
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_track_found(client_and_mocks):
    client, session, run_result, _ = client_and_mocks
    run_result.single.return_value = {
        "t": {"track_id": "abc", "title": "Song", "artist": "Art"}
    }

    result = await client.get_track("abc")
    assert result == {"track_id": "abc", "title": "Song", "artist": "Art"}


@pytest.mark.asyncio
async def test_get_track_not_found(client_and_mocks):
    client, session, run_result, _ = client_and_mocks
    run_result.single.return_value = None

    result = await client.get_track("nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# get_neighbors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_neighbors(client_and_mocks):
    client, session, run_result, _ = client_and_mocks

    # Make run_result async-iterable
    mock_records = [
        {"neighbor": {"track_id": "n1", "title": "N1"}, "frequency": 5},
        {"neighbor": {"track_id": "n2", "title": "N2"}, "frequency": 3},
    ]

    async def _aiter(self):
        for r in mock_records:
            yield r

    run_result.__aiter__ = _aiter

    result = await client.get_neighbors("abc", limit=10)

    assert len(result) == 2
    assert result[0]["track_id"] == "n1"
    assert result[0]["frequency"] == 5

    query = session.run.call_args.args[0]
    assert "TRANSITIONS_TO" in query
    assert "ORDER BY r.frequency DESC" in query
    params = session.run.call_args.args[1]
    assert params["limit"] == 10


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_stats(client_and_mocks):
    client, session, run_result, _ = client_and_mocks
    run_result.single.return_value = {
        "tracks": 100,
        "transitions": 250,
        "sets": 10,
        "djs": 5,
    }

    stats = await client.get_stats()
    assert stats == {"tracks": 100, "transitions": 250, "sets": 10, "djs": 5}


# ---------------------------------------------------------------------------
# search_tracks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_tracks(client_and_mocks):
    client, session, run_result, _ = client_and_mocks

    mock_records = [
        {"node": {"track_id": "s1", "title": "Hello"}, "score": 0.9},
    ]

    async def _aiter(self):
        for r in mock_records:
            yield r

    run_result.__aiter__ = _aiter

    result = await client.search_tracks("Hello", limit=5)

    assert len(result) == 1
    assert result[0]["title"] == "Hello"
    assert result[0]["score"] == 0.9

    query = session.run.call_args.args[0]
    assert "track_search" in query
    assert "ORDER BY score DESC" in query


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close(client_and_mocks):
    client, _, _, driver = client_and_mocks
    await client.close()
    driver.close.assert_awaited_once()
