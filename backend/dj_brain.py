"""Track selection + replanning logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.camelot import compatibility_score
from backend.models import Phase, SetState, TrackModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

WEIGHTS = {
    "frequency": 0.30,
    "harmonic": 0.25,
    "energy_arc": 0.25,
    "virality": 0.10,
    "self_play": 0.10,
}


# ---------------------------------------------------------------------------
# Energy arc models
# ---------------------------------------------------------------------------


def get_energy_target(elapsed_mins: float, set_length: float, arc_style: str = "club_night") -> float:
    """Return target energy (0.0–1.0) for a given point in the set."""
    if set_length <= 0:
        return 0.5
    pct = min(elapsed_mins / set_length, 1.0)

    if arc_style == "festival":
        if pct < 0.15:
            return 0.3 + (pct / 0.15) * 0.5  # 0.3 → 0.8
        if pct < 0.85:
            return 0.8 + ((pct - 0.15) / 0.70) * 0.2  # 0.8 → 1.0
        return 1.0 - ((pct - 0.85) / 0.15) * 0.6  # 1.0 → 0.4

    if arc_style == "lounge":
        return 0.4 + 0.1 * (0.5 - abs(pct - 0.5))  # flat ~0.4–0.45

    # club_night (default)
    if pct < 0.20:
        return 0.2 + (pct / 0.20) * 0.3  # 0.2 → 0.5
    if pct < 0.60:
        return 0.5 + ((pct - 0.20) / 0.40) * 0.4  # 0.5 → 0.9
    if pct < 0.85:
        return 0.9 + ((pct - 0.60) / 0.25) * 0.1  # 0.9 → 1.0
    return 1.0 - ((pct - 0.85) / 0.15) * 0.5  # 1.0 → 0.5


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass
class ScoredTrack:
    track: dict
    score: float
    breakdown: dict


def _score_candidate(
    current: TrackModel,
    candidate: dict,
    transition_freq: int,
    max_freq: int,
    set_state: SetState,
    arc_style: str = "club_night",
) -> ScoredTrack:
    """Score a single candidate track."""
    breakdown = {}

    # Frequency score
    breakdown["frequency"] = (transition_freq / max_freq) if max_freq > 0 else 0.0

    # Harmonic score
    if current.key and candidate.get("key"):
        breakdown["harmonic"] = compatibility_score(current.key, candidate["key"])
    else:
        breakdown["harmonic"] = 0.5  # neutral when key unknown

    # Energy arc fit
    target_energy = get_energy_target(set_state.elapsed_mins, set_state.set_length_mins, arc_style)
    candidate_energy = candidate.get("energy") or 0.5
    energy_diff = abs(target_energy - candidate_energy)
    breakdown["energy_arc"] = max(0.0, 1.0 - energy_diff * 2)

    # Virality (from transition edge data if available)
    breakdown["virality"] = min(candidate.get("virality_score", 0.0), 1.0)

    # Self-play quality (from transition edge data if available)
    breakdown["self_play"] = min(candidate.get("self_play_quality", 0.5), 1.0)

    total = sum(WEIGHTS[k] * breakdown[k] for k in WEIGHTS)

    return ScoredTrack(track=candidate, score=total, breakdown=breakdown)


def select_next(
    current: TrackModel,
    neighbors: list[dict],
    set_state: SetState,
    arc_style: str = "club_night",
) -> ScoredTrack | None:
    """Select the best next track from neighbor candidates.

    Each neighbor dict should have track properties + 'frequency' key.
    """
    if not neighbors:
        return None

    max_freq = max(n.get("frequency", 1) for n in neighbors)

    scored = [
        _score_candidate(
            current, n, n.get("frequency", 1), max_freq, set_state, arc_style
        )
        for n in neighbors
    ]

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[0]


# ---------------------------------------------------------------------------
# Request evaluation
# ---------------------------------------------------------------------------


@dataclass
class Evaluation:
    result: str  # "pass", "soft_fail", "hard_fail"
    reason: str


def evaluate_request(track: TrackModel, set_state: SetState) -> Evaluation:
    """Evaluate whether a guest-requested track fits the current set."""
    # BPM check — allow ±8 BPM from current
    if track.bpm and set_state.current_bpm:
        delta = abs(track.bpm - set_state.current_bpm)
        if delta > 8:
            return Evaluation("hard_fail", f"BPM too far from current ({delta:.0f} BPM difference)")
        if delta > 5:
            return Evaluation("soft_fail", f"BPM stretch ({delta:.0f} BPM difference)")

    # Genre check
    if set_state.genres and track.genre:
        overlap = set(g.lower() for g in track.genre) & set(g.lower() for g in set_state.genres)
        if not overlap:
            return Evaluation("soft_fail", f"Genre mismatch: {track.genre} vs set genres {set_state.genres}")

    return Evaluation("pass", "Track fits current set")


# ---------------------------------------------------------------------------
# Slot finding (stub — full implementation needs graph path finding)
# ---------------------------------------------------------------------------


@dataclass
class SlotResult:
    position: int
    eta_mins: float
    confidence: float


def find_slot(queue_length: int, avg_track_mins: float = 5.0) -> SlotResult:
    """Find the best slot for a new track in the queue.

    Stub implementation — places at end with estimated ETA.
    Full implementation in Phase 3 will use graph bridge paths.
    """
    position = queue_length
    eta = position * avg_track_mins
    confidence = 0.7 if position < 5 else 0.4
    return SlotResult(position=position, eta_mins=eta, confidence=confidence)
