"""Tests for TransitionLogger — quality signals and EMA scoring."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.transition_logger import QualitySignal, TransitionLog, TransitionLogger


# ---------------------------------------------------------------------------
# QualitySignal enum
# ---------------------------------------------------------------------------


def test_quality_signal_values():
    assert QualitySignal.SKIP == "skip"
    assert QualitySignal.OVERRIDE == "override"
    assert QualitySignal.COMPLETION == "completion"
    assert QualitySignal.ENERGY_CONTINUITY == "energy_continuity"
    assert QualitySignal.GUEST_PROXIMITY == "guest_proximity"
    assert len(QualitySignal) == 5


# ---------------------------------------------------------------------------
# TransitionLog
# ---------------------------------------------------------------------------


def test_transition_log_defaults():
    log = TransitionLog(from_track_id="a", to_track_id="b", transition_type="blend")
    assert log.from_track_id == "a"
    assert log.to_track_id == "b"
    assert log.transition_type == "blend"
    assert log.set_phase == ""
    assert log.source == "ai"
    assert log.signals == []
    assert isinstance(log.timestamp, datetime)


def test_quality_score_no_signals():
    log = TransitionLog(from_track_id="a", to_track_id="b", transition_type="blend")
    assert log.quality_score == 0.0


def test_quality_score_positive():
    log = TransitionLog(
        from_track_id="a", to_track_id="b", transition_type="blend",
        signals=[QualitySignal.COMPLETION, QualitySignal.ENERGY_CONTINUITY],
    )
    # 0.6 + 0.3 = 0.9
    assert log.quality_score == pytest.approx(0.9)


def test_quality_score_negative():
    log = TransitionLog(
        from_track_id="a", to_track_id="b", transition_type="blend",
        signals=[QualitySignal.SKIP],
    )
    assert log.quality_score == pytest.approx(-1.0)


def test_quality_score_mixed():
    log = TransitionLog(
        from_track_id="a", to_track_id="b", transition_type="blend",
        signals=[QualitySignal.SKIP, QualitySignal.COMPLETION],
    )
    # -1.0 + 0.6 = -0.4
    assert log.quality_score == pytest.approx(-0.4)


def test_quality_score_clamped_low():
    log = TransitionLog(
        from_track_id="a", to_track_id="b", transition_type="blend",
        signals=[QualitySignal.SKIP, QualitySignal.OVERRIDE],
    )
    # -1.0 + -0.8 = -1.8, clamped to -1.0
    assert log.quality_score == pytest.approx(-1.0)


def test_quality_score_clamped_high():
    log = TransitionLog(
        from_track_id="a", to_track_id="b", transition_type="blend",
        signals=[
            QualitySignal.COMPLETION,
            QualitySignal.ENERGY_CONTINUITY,
            QualitySignal.GUEST_PROXIMITY,
        ],
    )
    # 0.6 + 0.3 + 0.1 = 1.0 (exactly at limit)
    assert log.quality_score == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# TransitionLogger — basic operations
# ---------------------------------------------------------------------------


def test_logger_empty():
    tl = TransitionLogger()
    assert tl.total_transitions == 0
    assert tl.get_logs() == []
    assert tl.get_recent() == []


def test_log_transition():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend", set_phase="peak", source="admin")
    assert entry.from_track_id == "a"
    assert entry.to_track_id == "b"
    assert entry.set_phase == "peak"
    assert entry.source == "admin"
    assert tl.total_transitions == 1


def test_add_signal_by_index():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")
    tl.add_signal(0, QualitySignal.COMPLETION)
    logs = tl.get_logs()
    assert logs[0].signals == [QualitySignal.COMPLETION]


def test_add_signal_invalid_index():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")
    tl.add_signal(5, QualitySignal.SKIP)  # out of range, should not raise
    assert tl.get_logs()[0].signals == []


def test_add_signal_to_latest():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")
    tl.log_transition("b", "c", "cut")
    tl.add_signal_to_latest(QualitySignal.SKIP)
    logs = tl.get_logs()
    assert logs[0].signals == []
    assert logs[1].signals == [QualitySignal.SKIP]


def test_add_signal_to_latest_empty():
    tl = TransitionLogger()
    tl.add_signal_to_latest(QualitySignal.SKIP)  # no logs, should not raise


def test_get_recent():
    tl = TransitionLogger()
    for i in range(20):
        tl.log_transition(f"t{i}", f"t{i+1}", "blend")
    recent = tl.get_recent(5)
    assert len(recent) == 5
    assert recent[0].from_track_id == "t15"


def test_get_logs_returns_copy():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")
    logs = tl.get_logs()
    logs.clear()
    assert tl.total_transitions == 1


# ---------------------------------------------------------------------------
# Edge quality (EMA)
# ---------------------------------------------------------------------------


def test_edge_quality_no_data():
    tl = TransitionLogger()
    assert tl.get_edge_quality("a", "b") == 0.5  # neutral default


def test_edge_quality_no_signals():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")
    # No signals on transition — should still return neutral
    assert tl.get_edge_quality("a", "b") == 0.5


def test_edge_quality_single_positive():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend")
    entry.signals.append(QualitySignal.COMPLETION)
    # quality_score = 0.6, normalized = (0.6 + 1) / 2 = 0.8
    # EMA: 0.3 * 0.8 + 0.7 * 0.5 = 0.24 + 0.35 = 0.59
    assert tl.get_edge_quality("a", "b") == pytest.approx(0.59)


def test_edge_quality_single_negative():
    tl = TransitionLogger()
    entry = tl.log_transition("a", "b", "blend")
    entry.signals.append(QualitySignal.SKIP)
    # quality_score = -1.0, normalized = 0.0
    # EMA: 0.3 * 0.0 + 0.7 * 0.5 = 0.35
    assert tl.get_edge_quality("a", "b") == pytest.approx(0.35)


def test_edge_quality_multiple_transitions():
    tl = TransitionLogger()
    # First: positive
    e1 = tl.log_transition("a", "b", "blend")
    e1.signals.append(QualitySignal.COMPLETION)  # score 0.6, norm 0.8
    # Second: negative
    e2 = tl.log_transition("a", "b", "blend")
    e2.signals.append(QualitySignal.SKIP)  # score -1.0, norm 0.0

    # EMA step 1: 0.3 * 0.8 + 0.7 * 0.5 = 0.59
    # EMA step 2: 0.3 * 0.0 + 0.7 * 0.59 = 0.413
    assert tl.get_edge_quality("a", "b") == pytest.approx(0.413)


def test_edge_quality_different_edge():
    tl = TransitionLogger()
    e1 = tl.log_transition("a", "b", "blend")
    e1.signals.append(QualitySignal.SKIP)
    # Query different edge
    assert tl.get_edge_quality("b", "c") == 0.5


def test_edge_quality_ignores_unscored():
    tl = TransitionLogger()
    tl.log_transition("a", "b", "blend")  # no signals
    e2 = tl.log_transition("a", "b", "blend")
    e2.signals.append(QualitySignal.COMPLETION)
    # Only second transition counted
    # EMA: 0.3 * 0.8 + 0.7 * 0.5 = 0.59
    assert tl.get_edge_quality("a", "b") == pytest.approx(0.59)
