"""Tests for DJBrain — track selection, scoring, energy arcs."""

from __future__ import annotations

import pytest

from backend.dj_brain import (
    Evaluation,
    SlotResult,
    evaluate_request,
    find_slot,
    get_energy_target,
    select_next,
)
from backend.models import Phase, SetState, TrackModel


# ---------------------------------------------------------------------------
# Energy arc
# ---------------------------------------------------------------------------


class TestEnergyArc:
    def test_club_night_start_low(self):
        e = get_energy_target(0.0, 120.0, "club_night")
        assert e == pytest.approx(0.2, abs=0.05)

    def test_club_night_peak(self):
        e = get_energy_target(80.0, 120.0, "club_night")
        assert e >= 0.85

    def test_club_night_comedown(self):
        e = get_energy_target(120.0, 120.0, "club_night")
        assert e <= 0.6

    def test_festival_faster_build(self):
        e_fest = get_energy_target(15.0, 120.0, "festival")
        e_club = get_energy_target(15.0, 120.0, "club_night")
        assert e_fest > e_club

    def test_lounge_flat(self):
        e1 = get_energy_target(10.0, 120.0, "lounge")
        e2 = get_energy_target(60.0, 120.0, "lounge")
        assert abs(e1 - e2) < 0.1  # relatively flat

    def test_zero_length_returns_default(self):
        assert get_energy_target(10.0, 0.0) == 0.5

    def test_past_end_clamped(self):
        e = get_energy_target(200.0, 120.0, "club_night")
        assert 0.0 <= e <= 1.0


# ---------------------------------------------------------------------------
# select_next
# ---------------------------------------------------------------------------


class TestSelectNext:
    def test_returns_best_scored(self):
        current = TrackModel(title="A", artist="X", key="8A", bpm=126.0)
        neighbors = [
            {"track_id": "n1", "key": "8A", "energy": 0.5, "frequency": 10, "bpm": 126.0},
            {"track_id": "n2", "key": "3A", "energy": 0.5, "frequency": 2, "bpm": 126.0},
        ]
        state = SetState(elapsed_mins=30.0, set_length_mins=120.0)
        result = select_next(current, neighbors, state)
        assert result is not None
        assert result.track["track_id"] == "n1"  # higher freq + compatible key
        assert result.score > 0

    def test_empty_neighbors_returns_none(self):
        current = TrackModel(title="A", artist="X")
        result = select_next(current, [], SetState())
        assert result is None

    def test_no_key_uses_neutral_harmonic(self):
        current = TrackModel(title="A", artist="X")
        neighbors = [{"track_id": "n1", "frequency": 5}]
        state = SetState()
        result = select_next(current, neighbors, state)
        assert result is not None
        assert result.breakdown["harmonic"] == 0.5

    def test_score_breakdown_has_all_keys(self):
        current = TrackModel(title="A", artist="X", key="8A")
        neighbors = [{"track_id": "n1", "key": "9A", "frequency": 3}]
        result = select_next(current, neighbors, SetState())
        assert set(result.breakdown.keys()) == {"frequency", "harmonic", "energy_arc", "virality", "self_play"}


# ---------------------------------------------------------------------------
# evaluate_request
# ---------------------------------------------------------------------------


class TestEvaluateRequest:
    def test_pass_matching_track(self):
        track = TrackModel(title="T", artist="A", bpm=126.0, genre=["tech house"])
        state = SetState(current_bpm=127.0, genres=["tech house"])
        result = evaluate_request(track, state)
        assert result.result == "pass"

    def test_hard_fail_bpm_too_far(self):
        track = TrackModel(title="T", artist="A", bpm=140.0)
        state = SetState(current_bpm=126.0)
        result = evaluate_request(track, state)
        assert result.result == "hard_fail"
        assert "BPM" in result.reason

    def test_soft_fail_bpm_stretch(self):
        track = TrackModel(title="T", artist="A", bpm=132.0)
        state = SetState(current_bpm=126.0)
        result = evaluate_request(track, state)
        assert result.result == "soft_fail"

    def test_soft_fail_genre_mismatch(self):
        track = TrackModel(title="T", artist="A", genre=["drum and bass"])
        state = SetState(genres=["tech house"])
        result = evaluate_request(track, state)
        assert result.result == "soft_fail"

    def test_pass_no_bpm_info(self):
        track = TrackModel(title="T", artist="A")
        state = SetState()
        result = evaluate_request(track, state)
        assert result.result == "pass"

    def test_pass_genre_overlap(self):
        track = TrackModel(title="T", artist="A", genre=["tech house", "house"])
        state = SetState(genres=["house", "deep house"])
        result = evaluate_request(track, state)
        assert result.result == "pass"


# ---------------------------------------------------------------------------
# find_slot
# ---------------------------------------------------------------------------


class TestFindSlot:
    def test_empty_queue(self):
        result = find_slot(0)
        assert result.position == 0
        assert result.eta_mins == 0.0

    def test_queue_with_entries(self):
        result = find_slot(5)
        assert result.position == 5
        assert result.eta_mins == 25.0  # 5 * 5.0

    def test_confidence_decreases_with_depth(self):
        shallow = find_slot(2)
        deep = find_slot(10)
        assert shallow.confidence > deep.confidence
