"""Edge re-weighting — combines real DJ frequency, virality, and self-play quality (Phase 6.3-6.4)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.transition_logger import TransitionLogger

logger = logging.getLogger(__name__)

# Final edge weight formula:
#   real_dj_frequency × 0.5 + virality × 0.2 + self_play_quality × 0.3

WEIGHT_FREQUENCY = 0.5
WEIGHT_VIRALITY = 0.2
WEIGHT_SELF_PLAY = 0.3


@dataclass
class EdgeWeight:
    """Computed edge weight with component breakdown."""

    from_id: str
    to_id: str
    frequency_score: float  # normalized 0–1
    virality_score: float  # 0–1
    self_play_quality: float  # 0–1 (from TransitionLogger EMA)
    final_weight: float  # combined score


def compute_edge_weight(
    from_id: str,
    to_id: str,
    frequency: int,
    max_frequency: int,
    virality_score: float,
    transition_logger: TransitionLogger | None = None,
) -> EdgeWeight:
    """Compute final edge weight combining all three signals.

    Args:
        from_id: Source track ID.
        to_id: Target track ID.
        frequency: How often real DJs play this transition.
        max_frequency: Max frequency across all edges (for normalization).
        virality_score: How viral the sets containing this transition were (0–1).
        transition_logger: Optional logger for self-play quality signal.

    Returns:
        EdgeWeight with breakdown and final combined score.
    """
    # Normalize frequency to 0–1
    freq_score = (frequency / max_frequency) if max_frequency > 0 else 0.0

    # Clamp virality
    virality = max(0.0, min(1.0, virality_score))

    # Self-play quality from transition logger (EMA)
    if transition_logger is not None:
        self_play = transition_logger.get_edge_quality(from_id, to_id)
    else:
        self_play = 0.5  # neutral default

    final = (
        WEIGHT_FREQUENCY * freq_score
        + WEIGHT_VIRALITY * virality
        + WEIGHT_SELF_PLAY * self_play
    )

    return EdgeWeight(
        from_id=from_id,
        to_id=to_id,
        frequency_score=freq_score,
        virality_score=virality,
        self_play_quality=self_play,
        final_weight=final,
    )


def batch_reweight(
    edges: list[dict],
    transition_logger: TransitionLogger | None = None,
) -> list[EdgeWeight]:
    """Reweight a batch of edges.

    Each edge dict should have: from_id, to_id, frequency, virality_score.
    """
    if not edges:
        return []

    max_freq = max(e.get("frequency", 1) for e in edges)

    return [
        compute_edge_weight(
            from_id=e["from_id"],
            to_id=e["to_id"],
            frequency=e.get("frequency", 1),
            max_frequency=max_freq,
            virality_score=e.get("virality_score", 0.0),
            transition_logger=transition_logger,
        )
        for e in edges
    ]
