"""Tests for transition extractor."""

from __future__ import annotations

from scraper.transition_extractor import (
    ExtractionResult,
    compute_virality_score,
    extract_transitions,
    generate_track_id,
    transitions_to_graph_data,
)


# ---------------------------------------------------------------------------
# extract_transitions
# ---------------------------------------------------------------------------


def test_extract_basic():
    tracks = [
        {"title": "Losing It", "artist": "Fisher"},
        {"title": "Cola", "artist": "CamelPhat"},
        {"title": "Turn Off The Lights", "artist": "Chris Lake"},
    ]
    result = extract_transitions(tracks, source="youtube", dj_name="Fisher")
    assert result.track_count == 3
    assert len(result.transitions) == 2
    assert result.transitions[0].from_title == "Losing It"
    assert result.transitions[0].to_title == "Cola"
    assert result.transitions[1].from_title == "Cola"
    assert result.transitions[1].to_title == "Turn Off The Lights"
    assert result.source == "youtube"


def test_extract_single_track():
    tracks = [{"title": "Only One", "artist": "DJ"}]
    result = extract_transitions(tracks)
    assert result.track_count == 1
    assert len(result.transitions) == 0


def test_extract_empty():
    result = extract_transitions([])
    assert result.track_count == 0
    assert result.transitions == []


def test_extract_skips_missing_title():
    tracks = [
        {"title": "A", "artist": "X"},
        {"title": "", "artist": "Y"},
        {"title": "C", "artist": "Z"},
    ]
    result = extract_transitions(tracks)
    # A->""  is skipped, ""->C is skipped
    assert len(result.transitions) == 0
    assert len(result.errors) == 2


def test_extract_with_timestamps():
    tracks = [
        {"title": "A", "artist": "X", "timestamp_s": 0.0},
        {"title": "B", "artist": "Y", "timestamp_s": 300.0},
    ]
    result = extract_transitions(tracks)
    assert result.transitions[0].timestamp_s == 0.0


def test_extract_preserves_metadata():
    tracks = [
        {"title": "A", "artist": "X"},
        {"title": "B", "artist": "Y"},
    ]
    result = extract_transitions(
        tracks, source="1001tl", set_title="Ultra 2025", dj_name="Fisher", set_popularity=0.8
    )
    assert result.set_title == "Ultra 2025"
    assert result.dj_name == "Fisher"
    assert result.transitions[0].set_popularity == 0.8
    assert result.transitions[0].source == "1001tl"


# ---------------------------------------------------------------------------
# generate_track_id
# ---------------------------------------------------------------------------


def test_generate_track_id_basic():
    tid = generate_track_id("Fisher", "Losing It")
    assert tid == "fisher::losing it"


def test_generate_track_id_normalizes():
    id1 = generate_track_id("  Fisher  ", "  Losing It  ")
    id2 = generate_track_id("fisher", "losing it")
    assert id1 == id2


def test_generate_track_id_strips_mix_tags():
    id1 = generate_track_id("Fisher", "Losing It (Original Mix)")
    id2 = generate_track_id("Fisher", "Losing It")
    assert id1 == id2


def test_generate_track_id_extended_mix():
    id1 = generate_track_id("Fisher", "Losing It (Extended Mix)")
    id2 = generate_track_id("Fisher", "Losing It")
    assert id1 == id2


# ---------------------------------------------------------------------------
# compute_virality_score
# ---------------------------------------------------------------------------


def test_virality_zero_views():
    assert compute_virality_score(view_count=0) == 0.0


def test_virality_high_views():
    score = compute_virality_score(view_count=1_000_000, max_view_count=1_000_000)
    assert 0.7 <= score <= 1.0


def test_virality_moderate_views():
    score = compute_virality_score(view_count=100_000, max_view_count=1_000_000)
    assert 0.3 <= score <= 0.8


def test_virality_with_likes():
    score_no_likes = compute_virality_score(view_count=100_000)
    score_with_likes = compute_virality_score(view_count=100_000, like_count=10_000)
    assert score_with_likes > score_no_likes


def test_virality_clamped():
    score = compute_virality_score(view_count=10_000_000, max_view_count=100)
    assert score <= 1.0


# ---------------------------------------------------------------------------
# transitions_to_graph_data
# ---------------------------------------------------------------------------


def test_transitions_to_graph_data():
    tracks = [
        {"title": "A", "artist": "X"},
        {"title": "B", "artist": "Y"},
        {"title": "C", "artist": "Z"},
    ]
    result = extract_transitions(tracks, source="youtube", set_popularity=0.5)
    graph_data = transitions_to_graph_data(result)

    assert len(graph_data) == 2
    assert graph_data[0]["from_id"] == "x::a"
    assert graph_data[0]["to_id"] == "y::b"
    assert graph_data[0]["source"] == "youtube"
    assert graph_data[0]["virality_score"] == 0.5


def test_transitions_to_graph_data_empty():
    result = ExtractionResult()
    assert transitions_to_graph_data(result) == []
