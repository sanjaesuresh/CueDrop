"""Transition logging and quality signal collection (Phase 6)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualitySignal(str, Enum):
    SKIP = "skip"  # admin skipped during/after transition
    OVERRIDE = "override"  # admin requested different track right after
    COMPLETION = "completion"  # track played to outro without intervention
    ENERGY_CONTINUITY = "energy_continuity"  # RMS energy didn't drop unexpectedly
    GUEST_PROXIMITY = "guest_proximity"  # guest requests increased after sequence


# Signal weights for computing quality score
_SIGNAL_WEIGHTS: dict[QualitySignal, float] = {
    QualitySignal.SKIP: -1.0,
    QualitySignal.OVERRIDE: -0.8,
    QualitySignal.COMPLETION: 0.6,
    QualitySignal.ENERGY_CONTINUITY: 0.3,
    QualitySignal.GUEST_PROXIMITY: 0.1,
}


@dataclass
class TransitionLog:
    """Record of an executed transition."""

    from_track_id: str
    to_track_id: str
    transition_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    set_phase: str = ""
    source: str = "ai"  # ai, admin, guest
    signals: list[QualitySignal] = field(default_factory=list)

    @property
    def quality_score(self) -> float:
        """Compute quality score from signals. Range: -1.0 to 1.0."""
        if not self.signals:
            return 0.0
        total = sum(_SIGNAL_WEIGHTS.get(s, 0.0) for s in self.signals)
        return max(-1.0, min(1.0, total))


class TransitionLogger:
    """Log transitions and compute edge quality scores."""

    def __init__(self) -> None:
        self._logs: list[TransitionLog] = []

    def log_transition(
        self,
        from_track_id: str,
        to_track_id: str,
        transition_type: str,
        set_phase: str = "",
        source: str = "ai",
    ) -> TransitionLog:
        """Record a new transition."""
        entry = TransitionLog(
            from_track_id=from_track_id,
            to_track_id=to_track_id,
            transition_type=transition_type,
            set_phase=set_phase,
            source=source,
        )
        self._logs.append(entry)
        return entry

    def add_signal(self, log_index: int, signal: QualitySignal) -> None:
        """Add a quality signal to a logged transition."""
        if 0 <= log_index < len(self._logs):
            self._logs[log_index].signals.append(signal)

    def add_signal_to_latest(self, signal: QualitySignal) -> None:
        """Add a quality signal to the most recent transition."""
        if self._logs:
            self._logs[-1].signals.append(signal)

    def get_edge_quality(self, from_id: str, to_id: str) -> float:
        """Compute exponential moving average quality for an edge.

        More recent transitions have higher weight (EMA with alpha=0.3).
        """
        relevant = [
            log for log in self._logs
            if log.from_track_id == from_id and log.to_track_id == to_id
            and log.signals  # only scored transitions
        ]
        if not relevant:
            return 0.5  # neutral default

        alpha = 0.3
        ema = 0.5  # start at neutral
        for log in relevant:
            # Normalize quality_score from [-1, 1] to [0, 1]
            normalized = (log.quality_score + 1.0) / 2.0
            ema = alpha * normalized + (1 - alpha) * ema

        return ema

    def get_logs(self) -> list[TransitionLog]:
        return list(self._logs)

    def get_recent(self, count: int = 10) -> list[TransitionLog]:
        return list(self._logs[-count:])

    @property
    def total_transitions(self) -> int:
        return len(self._logs)
