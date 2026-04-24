"""Transition extractor — converts ordered tracklists into graph edges (Phase 2 A.3)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTransition:
    """A transition edge extracted from a tracklist."""

    from_title: str
    from_artist: str
    to_title: str
    to_artist: str
    source: str  # e.g., "1001tl", "youtube", "tiktok"
    set_popularity: float = 0.0  # view count or similar metric, normalized
    timestamp_s: float | None = None  # when in the set this transition occurred


@dataclass
class ExtractionResult:
    """Result of extracting transitions from a tracklist."""

    transitions: list[ExtractedTransition] = field(default_factory=list)
    track_count: int = 0
    source: str = ""
    set_title: str = ""
    dj_name: str = ""
    errors: list[str] = field(default_factory=list)


def extract_transitions(
    tracks: list[dict],
    source: str = "unknown",
    set_title: str = "",
    dj_name: str = "",
    set_popularity: float = 0.0,
) -> ExtractionResult:
    """Extract transition edges from an ordered tracklist.

    Each track dict should have at least 'title' and 'artist' keys.
    Optional: 'timestamp_s' for timing information.

    Args:
        tracks: Ordered list of track dicts.
        source: Source identifier (e.g., "1001tl", "youtube").
        set_title: Name of the DJ set.
        dj_name: DJ who played the set.
        set_popularity: Normalized popularity metric (0–1).

    Returns:
        ExtractionResult with list of transitions.
    """
    result = ExtractionResult(
        track_count=len(tracks),
        source=source,
        set_title=set_title,
        dj_name=dj_name,
    )

    if len(tracks) < 2:
        return result

    for i in range(len(tracks) - 1):
        current = tracks[i]
        next_track = tracks[i + 1]

        from_title = current.get("title", "").strip()
        from_artist = current.get("artist", "").strip()
        to_title = next_track.get("title", "").strip()
        to_artist = next_track.get("artist", "").strip()

        if not from_title or not to_title:
            result.errors.append(f"Skipping transition at position {i}: missing title")
            continue

        transition = ExtractedTransition(
            from_title=from_title,
            from_artist=from_artist,
            to_title=to_title,
            to_artist=to_artist,
            source=source,
            set_popularity=set_popularity,
            timestamp_s=current.get("timestamp_s"),
        )
        result.transitions.append(transition)

    return result


def generate_track_id(artist: str, title: str) -> str:
    """Generate a deterministic track ID from artist and title.

    Normalizes to lowercase, strips whitespace, removes common
    suffixes like remix tags for matching.
    """
    normalized_artist = artist.lower().strip()
    normalized_title = title.lower().strip()

    # Remove common noise
    for noise in ["(original mix)", "(extended mix)", "(radio edit)"]:
        normalized_title = normalized_title.replace(noise, "").strip()

    return f"{normalized_artist}::{normalized_title}"


def compute_virality_score(
    view_count: int = 0,
    like_count: int = 0,
    max_view_count: int = 1_000_000,
) -> float:
    """Compute a virality score from engagement metrics.

    Returns a 0–1 score based on view/like counts relative to baseline.
    """
    if max_view_count <= 0:
        return 0.0

    # Log-scale normalization for view counts
    import math

    if view_count <= 0:
        view_score = 0.0
    else:
        view_score = min(1.0, math.log10(view_count + 1) / math.log10(max_view_count + 1))

    # Like ratio bonus (if available)
    like_bonus = 0.0
    if like_count > 0 and view_count > 0:
        like_ratio = like_count / view_count
        like_bonus = min(0.2, like_ratio * 2)  # cap at 0.2 bonus

    return min(1.0, view_score * 0.8 + like_bonus)


def transitions_to_graph_data(
    result: ExtractionResult,
) -> list[dict]:
    """Convert extraction result to graph-ready dicts.

    Returns list of dicts with from_id, to_id, source, virality_score
    suitable for GraphClient.upsert_transition.
    """
    graph_data = []

    for t in result.transitions:
        from_id = generate_track_id(t.from_artist, t.from_title)
        to_id = generate_track_id(t.to_artist, t.to_title)

        graph_data.append({
            "from_id": from_id,
            "to_id": to_id,
            "from_title": t.from_title,
            "from_artist": t.from_artist,
            "to_title": t.to_title,
            "to_artist": t.to_artist,
            "source": t.source,
            "virality_score": t.set_popularity,
        })

    return graph_data
