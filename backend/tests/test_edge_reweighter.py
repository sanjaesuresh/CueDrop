"""Tests for edge re-weighting — final weight computation."""

from __future__ import annotations

import pytest

from backend.edge_reweighter import (
    WEIGHT_FREQUENCY,
    WEIGHT_SELF_PLAY,
    WEIGHT_VIRALITY,
    EdgeWeight,
    batch_reweight,
    compute_edge_weight,
)
from backend.transition_logger import QualitySignal, TransitionLogger


# ---------------------------------------------------------------------------
# compute_edge_weight — basic
# ---------------------------------------------------------------------------


def test_compute_edge_weight_neutral():
    """No logger, mid-range values."""
    ew = compute_edge_weight("a", "b", frequency=5, max_frequency=10, virality_score=0.5)
    assert ew.from_id == "a"
    assert ew.to_id == "b"
    assert ew.frequency_score == pytest.approx(0.5)
    assert ew.virality_score == pytest.approx(0.5)
    assert ew.self_play_quality == pytest.approx(0.5)  # neutral default
    expected = 0.5 * 0.5 + 0.2 * 0.5 + 0.3 * 0.5
    assert ew.final_weight == pytest.approx(expected)


def test_compute_edge_weight_max_frequency():
    ew = compute_edge_weight("a", "b", frequency=10, max_frequency=10, virality_score=1.0)
    assert ew.frequency_score == pytest.approx(1.0)
    assert ew.final_weight == pytest.approx(WEIGHT_FREQUENCY + WEIGHT_VIRALITY + WEIGHT_SELF_PLAY * 0.5)


def test_compute_edge_weight_zero_frequency():
    ew = compute_edge_weight("a", "b", frequency=0, max_frequency=10, virality_score=0.0)
    assert ew.frequency_score == pytest.approx(0.0)
    assert ew.virality_score == pytest.approx(0.0)
    assert ew.final_weight == pytest.approx(WEIGHT_SELF_PLAY * 0.5)


def test_compute_edge_weight_zero_max_frequency():
    ew = compute_edge_weight("a", "b", frequency=5, max_frequency=0, virality_score=0.5)
    assert ew.frequency_score == pytest.approx(0.0)


def test_virality_clamped():
    ew = compute_edge_weight("a", "b", frequency=1, max_frequency=1, virality_score=2.5)
    assert ew.virality_score == pytest.approx(1.0)

    ew2 = compute_edge_weight("a", "b", frequency=1, max_frequency=1, virality_score=-0.5)
    assert ew2.virality_score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# compute_edge_weight — with TransitionLogger
# ---------------------------------------------------------------------------


def test_with_logger_positive_signal():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend")
    entry.signals.append(QualitySignal.COMPLETION)
    # EMA: 0.3 * 0.8 + 0.7 * 0.5 = 0.59

    ew = compute_edge_weight("a", "b", frequency=5, max_frequency=10,
                             virality_score=0.3, transition_logger=tl)
    assert ew.self_play_quality == pytest.approx(0.59)
    assert ew.final_weight > 0


def test_with_logger_negative_signal():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend")
    entry.signals.append(QualitySignal.SKIP)
    # EMA: 0.3 * 0.0 + 0.7 * 0.5 = 0.35

    ew = compute_edge_weight("a", "b", frequency=5, max_frequency=10,
                             virality_score=0.3, transition_logger=tl)
    assert ew.self_play_quality == pytest.approx(0.35)


def test_with_logger_no_signals_for_edge():
    tl = TransitionLogger()
    tl.log_transition("x", "y", "blend")  # different edge

    ew = compute_edge_weight("a", "b", frequency=5, max_frequency=10,
                             virality_score=0.3, transition_logger=tl)
    assert ew.self_play_quality == pytest.approx(0.5)  # neutral


# ---------------------------------------------------------------------------
# Weight constants
# ---------------------------------------------------------------------------


def test_weights_sum_to_one():
    assert WEIGHT_FREQUENCY + WEIGHT_VIRALITY + WEIGHT_SELF_PLAY == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# batch_reweight
# ---------------------------------------------------------------------------


def test_batch_reweight_empty():
    assert batch_reweight([]) == []


def test_batch_reweight_multiple():
    edges = [
        {"from_id": "a", "to_id": "b", "frequency": 10, "virality_score": 0.8},
        {"from_id": "b", "to_id": "c", "frequency": 5, "virality_score": 0.2},
        {"from_id": "c", "to_id": "d", "frequency": 1, "virality_score": 0.0},
    ]
    results = batch_reweight(edges)
    assert len(results) == 3
    # First edge has max frequency (10/10 = 1.0)
    assert results[0].frequency_score == pytest.approx(1.0)
    # Weights should be descending (higher freq + virality = higher weight)
    assert results[0].final_weight > results[1].final_weight
    assert results[1].final_weight > results[2].final_weight


def test_batch_reweight_with_logger():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend")
    entry.signals.append(QualitySignal.COMPLETION)

    edges = [
        {"from_id": "a", "to_id": "b", "frequency": 5, "virality_score": 0.5},
        {"from_id": "b", "to_id": "c", "frequency": 5, "virality_score": 0.5},
    ]
    results = batch_reweight(edges, transition_logger=tl)
    # Edge a->b should have higher self_play than b->c
    assert results[0].self_play_quality > results[1].self_play_quality
    assert results[0].final_weight > results[1].final_weight


def test_batch_reweight_normalizes_frequency():
    edges = [
        {"from_id": "a", "to_id": "b", "frequency": 100},
        {"from_id": "b", "to_id": "c", "frequency": 50},
    ]
    results = batch_reweight(edges)
    assert results[0].frequency_score == pytest.approx(1.0)
    assert results[1].frequency_score == pytest.approx(0.5)
