"""Tests for DJBrain — track selection, scoring, energy arcs."""

from __future__ import annotations

import pytest

from backend.dj_brain import (
    BridgeResult,
    Evaluation,
    SlotResult,
    _hop_cost,
    build_bridge_path,
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


# ---------------------------------------------------------------------------
# _hop_cost
# ---------------------------------------------------------------------------


class TestHopCost:
    def test_same_track_zero_bpm_delta(self):
        t = {"bpm": 126, "key": "8A", "energy": 0.5, "frequency": 5}
        cost = _hop_cost(t, t)
        assert cost < 0.5  # low cost for identical track

    def test_bpm_too_far_infinite(self):
        a = {"bpm": 120, "key": "8A"}
        b = {"bpm": 128, "key": "8A"}  # delta = 8 > MAX_BPM_DELTA_PER_HOP (3)
        assert _hop_cost(a, b) == float("inf")

    def test_compatible_key_lower_cost(self):
        a = {"bpm": 126, "key": "8A", "energy": 0.5}
        b_compat = {"bpm": 127, "key": "9A", "energy": 0.5}
        b_incompat = {"bpm": 127, "key": "3B", "energy": 0.5}
        assert _hop_cost(a, b_compat) < _hop_cost(a, b_incompat)

    def test_no_bpm_neutral(self):
        a = {"key": "8A"}
        b = {"key": "8A"}
        cost = _hop_cost(a, b)
        assert 0 < cost < 1

    def test_high_frequency_lowers_cost(self):
        a = {"bpm": 126, "key": "8A", "energy": 0.5}
        b_pop = {"bpm": 127, "key": "8A", "energy": 0.5, "frequency": 20}
        b_rare = {"bpm": 127, "key": "8A", "energy": 0.5, "frequency": 1}
        assert _hop_cost(a, b_pop) < _hop_cost(a, b_rare)


# ---------------------------------------------------------------------------
# build_bridge_path
# ---------------------------------------------------------------------------


def _make_graph():
    """Build a simple test graph for bridge path finding.

    Graph: A(120,8A) -> B(122,8A) -> C(124,9A) -> D(126,9A)
    """
    tracks = {
        "A": {"id": "A", "bpm": 120, "key": "8A", "energy": 0.4, "frequency": 5},
        "B": {"id": "B", "bpm": 122, "key": "8A", "energy": 0.5, "frequency": 8},
        "C": {"id": "C", "bpm": 124, "key": "9A", "energy": 0.6, "frequency": 6},
        "D": {"id": "D", "bpm": 126, "key": "9A", "energy": 0.7, "frequency": 4},
    }
    edges = {
        "A": ["B"],
        "B": ["C"],
        "C": ["D"],
        "D": [],
    }

    def neighbors(track_id: str) -> list[dict]:
        return [tracks[n] for n in edges.get(track_id, []) if n in tracks]

    return tracks, neighbors


class TestBuildBridgePath:
    def test_direct_hop_feasible(self):
        tracks, neighbors = _make_graph()
        result = build_bridge_path(tracks["A"], tracks["B"], neighbors)
        assert result.feasible
        assert result.total_cost < float("inf")

    def test_same_track(self):
        tracks, neighbors = _make_graph()
        result = build_bridge_path(tracks["A"], tracks["A"], neighbors)
        assert result.feasible
        assert result.path == []
        assert result.total_cost == 0.0

    def test_multi_hop_path(self):
        tracks, neighbors = _make_graph()
        # A->D requires going through B and C (BPM delta A->D = 6, too big for direct)
        result = build_bridge_path(tracks["A"], tracks["D"], neighbors, max_hops=4)
        assert result.feasible
        assert len(result.path) >= 1  # at least one intermediate

    def test_no_path_infeasible(self):
        tracks, neighbors = _make_graph()
        # D has no outgoing edges, so D -> A is infeasible
        isolated = {"id": "Z", "bpm": 200, "key": "1B", "energy": 0.9}
        result = build_bridge_path(tracks["A"], isolated, neighbors)
        assert not result.feasible

    def test_empty_from_track(self):
        result = build_bridge_path({}, {"id": "B"}, lambda x: [])
        assert not result.feasible

    def test_large_bpm_gap_needs_intermediates(self):
        """When BPM gap > 3, direct hop fails but bridge should work."""
        tracks, neighbors = _make_graph()
        direct_cost = _hop_cost(tracks["A"], tracks["D"])
        assert direct_cost == float("inf")  # too far for direct

        result = build_bridge_path(tracks["A"], tracks["D"], neighbors, max_hops=4)
        assert result.feasible

    def test_max_hops_limits_search(self):
        tracks, neighbors = _make_graph()
        # With max_hops=0, only direct hop is checked
        result = build_bridge_path(tracks["A"], tracks["D"], neighbors, max_hops=0)
        # Direct hop A->D fails (BPM delta = 6), so should be infeasible
        assert not result.feasible

    def test_path_avoids_cycles(self):
        """Graph with cycle should not produce infinite loops."""
        tracks = {
            "A": {"id": "A", "bpm": 120, "key": "8A", "energy": 0.5, "frequency": 5},
            "B": {"id": "B", "bpm": 122, "key": "8A", "energy": 0.5, "frequency": 5},
            "C": {"id": "C", "bpm": 124, "key": "9A", "energy": 0.6, "frequency": 5},
        }
        edges = {"A": ["B"], "B": ["A", "C"], "C": ["B"]}

        def neighbors(tid):
            return [tracks[n] for n in edges.get(tid, [])]

        target = {"id": "T", "bpm": 124, "key": "9A", "energy": 0.6}
        result = build_bridge_path(tracks["A"], target, neighbors, max_hops=5)
        # Should terminate without hanging
        assert isinstance(result, BridgeResult)
