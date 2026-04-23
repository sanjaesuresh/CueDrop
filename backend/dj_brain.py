"""Track selection + replanning logic."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.camelot import compatibility_score, is_compatible
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


# ---------------------------------------------------------------------------
# Bridge path finding
# ---------------------------------------------------------------------------

MAX_BPM_DELTA_PER_HOP = 3.0


@dataclass
class BridgeResult:
    """Result of bridge path finding."""

    path: list[dict]  # intermediate tracks (excludes from/to)
    total_cost: float
    feasible: bool


def _hop_cost(from_track: dict, to_track: dict) -> float:
    """Compute cost of a single hop between two tracks.

    Lower is better. Factors: BPM delta, key compatibility, energy smoothness.
    Returns float('inf') if hop violates hard constraints.
    """
    from_bpm = from_track.get("bpm") or 0
    to_bpm = to_track.get("bpm") or 0

    # Hard constraint: BPM shift per hop
    if from_bpm and to_bpm:
        bpm_delta = abs(from_bpm - to_bpm)
        if bpm_delta > MAX_BPM_DELTA_PER_HOP:
            return float("inf")
        bpm_cost = bpm_delta / MAX_BPM_DELTA_PER_HOP
    else:
        bpm_cost = 0.5  # unknown BPM, neutral

    # Key compatibility
    from_key = from_track.get("key", "")
    to_key = to_track.get("key", "")
    if from_key and to_key:
        key_cost = 1.0 - compatibility_score(from_key, to_key)
    else:
        key_cost = 0.3  # neutral

    # Energy smoothness
    from_energy = from_track.get("energy") or 0.5
    to_energy = to_track.get("energy") or 0.5
    energy_cost = abs(from_energy - to_energy)

    # Inverse frequency — prefer popular transitions
    freq = to_track.get("frequency", 1)
    freq_bonus = min(1.0, freq / 10.0)  # cap at 10
    freq_cost = 1.0 - freq_bonus

    return bpm_cost * 0.35 + key_cost * 0.30 + energy_cost * 0.15 + freq_cost * 0.20


def build_bridge_path(
    from_track: dict,
    to_track: dict,
    graph_neighbors_fn,
    max_hops: int = 4,
) -> BridgeResult:
    """Find intermediate tracks to bridge from one track to another.

    Uses beam search (width=10) through the graph, scoring each candidate
    path by cumulative hop cost. Prefers paths that gradually shift BPM
    and maintain harmonic compatibility.

    Args:
        from_track: Starting track dict (must have id, bpm, key, energy).
        to_track: Target track dict.
        graph_neighbors_fn: Callable(track_id) -> list[dict] returning neighbors.
        max_hops: Maximum intermediate tracks (default 4).

    Returns:
        BridgeResult with the best path found.
    """
    if not from_track or not to_track:
        return BridgeResult(path=[], total_cost=float("inf"), feasible=False)

    from_id = from_track.get("id", "")
    to_id = to_track.get("id", "")

    if from_id == to_id:
        return BridgeResult(path=[], total_cost=0.0, feasible=True)

    # Check if direct hop is feasible
    direct_cost = _hop_cost(from_track, to_track)
    if direct_cost < float("inf"):
        return BridgeResult(path=[], total_cost=direct_cost, feasible=True)

    beam_width = 10
    # Each beam entry: (total_cost, [intermediate_track_dicts], last_track_dict)
    beam: list[tuple[float, list[dict], dict]] = [(0.0, [], from_track)]
    best_result = BridgeResult(path=[], total_cost=float("inf"), feasible=False)
    visited_global: set[str] = {from_id}

    for hop in range(max_hops):
        candidates: list[tuple[float, list[dict], dict]] = []

        for cost_so_far, path_so_far, last_track in beam:
            last_id = last_track.get("id", "")
            neighbors = graph_neighbors_fn(last_id)

            for neighbor in neighbors:
                n_id = neighbor.get("id", "")
                if n_id in visited_global or n_id == from_id:
                    continue

                hop_c = _hop_cost(last_track, neighbor)
                if hop_c == float("inf"):
                    continue

                new_cost = cost_so_far + hop_c
                new_path = path_so_far + [neighbor]

                # Check if this neighbor can reach the target
                final_hop = _hop_cost(neighbor, to_track)
                if final_hop < float("inf"):
                    total = new_cost + final_hop
                    if total < best_result.total_cost:
                        best_result = BridgeResult(
                            path=new_path, total_cost=total, feasible=True
                        )

                candidates.append((new_cost, new_path, neighbor))

        if not candidates:
            break

        # Keep top beam_width candidates
        candidates.sort(key=lambda c: c[0])
        beam = candidates[:beam_width]

        # Track visited to avoid cycles
        for _, _, last in beam:
            visited_global.add(last.get("id", ""))

    return best_result
