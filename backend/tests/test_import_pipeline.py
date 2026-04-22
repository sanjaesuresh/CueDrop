"""Tests for import_pipeline — mocked GraphClient."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from backend.import_pipeline import ImportResult, import_directory, import_file


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_graph() -> AsyncMock:
    graph = AsyncMock()
    graph.upsert_track.return_value = "mock_track_id"
    return graph


def _minimal_set(dj: str = "TestDJ", n_tracks: int = 3) -> dict:
    return {
        "dj": dj,
        "event": "Test Event",
        "tracks": [
            {"title": f"Track {i}", "artist": f"Artist {i}"}
            for i in range(n_tracks)
        ],
    }


# ---------------------------------------------------------------------------
# ImportResult
# ---------------------------------------------------------------------------


def test_import_result_defaults():
    r = ImportResult()
    assert r.tracks_added == 0
    assert r.transitions_created == 0
    assert r.sets_imported == 0
    assert r.errors == []


def test_import_result_merge():
    a = ImportResult(tracks_added=3, transitions_created=2, sets_imported=1, errors=["e1"])
    b = ImportResult(tracks_added=5, transitions_created=4, sets_imported=2, errors=["e2"])
    a.merge(b)
    assert a.tracks_added == 8
    assert a.transitions_created == 6
    assert a.sets_imported == 3
    assert a.errors == ["e1", "e2"]


# ---------------------------------------------------------------------------
# import_file — single set
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_single_set():
    graph = _mock_graph()
    data = _minimal_set(n_tracks=4)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = await import_file(f.name, graph)

    assert result.sets_imported == 1
    assert result.tracks_added == 4
    assert result.transitions_created == 3
    assert result.errors == []
    graph.upsert_dj.assert_called()
    graph.upsert_set.assert_called_once()


# ---------------------------------------------------------------------------
# import_file — list of sets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_list_of_sets():
    graph = _mock_graph()
    data = [_minimal_set("DJ_A", 3), _minimal_set("DJ_B", 5)]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = await import_file(f.name, graph)

    assert result.sets_imported == 2
    assert result.tracks_added == 8  # 3 + 5
    assert result.transitions_created == 6  # 2 + 4
    assert result.errors == []


# ---------------------------------------------------------------------------
# import_file — malformed record skipped
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_skips_malformed():
    graph = _mock_graph()
    # Missing required "tracks" field
    data = [{"dj": "Good", "tracks": [{"title": "T", "artist": "A"}]}, {"dj": "Bad"}]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = await import_file(f.name, graph)

    assert result.sets_imported == 1
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# import_file — invalid JSON
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_invalid_json():
    graph = _mock_graph()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        f.flush()
        result = await import_file(f.name, graph)

    assert result.sets_imported == 0
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# import_file — missing file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_missing_file():
    graph = _mock_graph()
    result = await import_file("/nonexistent/path.json", graph)
    assert result.sets_imported == 0
    assert len(result.errors) == 1


# ---------------------------------------------------------------------------
# import_file — dj as DJModel dict
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_file_dj_as_dict():
    graph = _mock_graph()
    data = {
        "dj": {"name": "Fisher", "genres": ["tech house"]},
        "tracks": [{"title": "Losing It", "artist": "Fisher"}],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = await import_file(f.name, graph)

    assert result.sets_imported == 1
    assert result.errors == []


# ---------------------------------------------------------------------------
# import_directory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_directory():
    graph = _mock_graph()

    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(3):
            p = Path(tmpdir) / f"set_{i}.json"
            p.write_text(json.dumps(_minimal_set(f"DJ_{i}", 2)))

        result = await import_directory(tmpdir, graph)

    assert result.sets_imported == 3
    assert result.tracks_added == 6
    assert result.transitions_created == 3  # 1 per set (2 tracks = 1 transition)
    assert result.errors == []


@pytest.mark.asyncio
async def test_import_directory_not_a_dir():
    graph = _mock_graph()
    result = await import_directory("/nonexistent/dir", graph)
    assert result.sets_imported == 0
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_import_directory_empty():
    graph = _mock_graph()

    with tempfile.TemporaryDirectory() as tmpdir:
        result = await import_directory(tmpdir, graph)

    assert result.sets_imported == 0
    assert result.errors == []


# ---------------------------------------------------------------------------
# import_file with sample fixtures
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_import_sample_fixtures():
    """Validate that sample_sets.json parses and imports without errors."""
    graph = _mock_graph()
    fixtures_path = str(Path(__file__).parent.parent / "fixtures" / "sample_sets.json")
    result = await import_file(fixtures_path, graph)

    assert result.sets_imported == 5
    assert result.tracks_added == 60  # 12+11+13+13+11
    assert result.errors == []
