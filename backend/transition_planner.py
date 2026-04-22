"""Transition planning — type selection, timing, and VDJscript generation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from backend.camelot import is_compatible
from backend.models import SetState, TrackModel, TransitionType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VDJscript command
# ---------------------------------------------------------------------------


@dataclass
class VDJCommand:
    """A timed VDJscript command."""

    script: str
    offset_ms: int = 0  # ms from transition start


@dataclass
class TransitionPlan:
    """Full transition plan between two tracks."""

    transition_type: TransitionType
    start_bar: int
    duration_bars: int
    bpm: float
    commands: list[VDJCommand] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        if self.bpm <= 0:
            return 0
        ms_per_bar = (60_000 / self.bpm) * 4  # 4 beats per bar
        return int(ms_per_bar * self.duration_bars)


# ---------------------------------------------------------------------------
# Transition type selection
# ---------------------------------------------------------------------------


def select_transition_type(
    current: TrackModel,
    next_track: TrackModel,
    set_state: SetState,
) -> TransitionType:
    """Choose the best transition type based on track properties and set state."""
    bpm_delta = abs((current.bpm or 0) - (next_track.bpm or 0))
    energy_current = current.energy or 0.5
    energy_next = next_track.energy or 0.5
    energy_delta = abs(energy_current - energy_next)

    # Large BPM jump → cut
    if bpm_delta > 5:
        return TransitionType.CUT

    # Genre boundary → filter sweep or echo out
    if current.genre and next_track.genre:
        current_genres = set(g.lower() for g in current.genre)
        next_genres = set(g.lower() for g in next_track.genre)
        if not current_genres & next_genres:
            return TransitionType.FILTER_SWEEP

    # Big energy jump at peak → bass swap
    if energy_delta > 0.3 and set_state.phase.value == "peak":
        return TransitionType.BASS_SWAP

    # Small BPM jump (3-5) → bass swap with pitch ride
    if 3 <= bpm_delta <= 5:
        return TransitionType.BASS_SWAP

    # Compatible key, similar BPM → blend
    if current.key and next_track.key:
        try:
            if is_compatible(current.key, next_track.key):
                return TransitionType.BLEND
        except ValueError:
            pass

    # Default to blend
    return TransitionType.BLEND


# ---------------------------------------------------------------------------
# Phrase alignment
# ---------------------------------------------------------------------------


def calculate_start_bar(
    current_position_bars: int,
    phrase_length: int = 16,
) -> int:
    """Find the next phrase boundary for transition start."""
    remainder = current_position_bars % phrase_length
    if remainder == 0:
        return current_position_bars
    return current_position_bars + (phrase_length - remainder)


# ---------------------------------------------------------------------------
# VDJscript builders per transition type
# ---------------------------------------------------------------------------


def _build_blend(incoming_deck: int, outgoing_deck: int, duration_ms: int) -> list[VDJCommand]:
    """16-bar crossfade with EQ matching."""
    step = duration_ms // 4
    return [
        VDJCommand(f"deck {incoming_deck} play", 0),
        VDJCommand(f"crossfader 25%", step),
        VDJCommand(f"crossfader 50%", step * 2),
        VDJCommand(f"crossfader 75%", step * 3),
        VDJCommand(f"crossfader 100%", duration_ms),
        VDJCommand(f"deck {outgoing_deck} stop", duration_ms + 500),
    ]


def _build_bass_swap(incoming_deck: int, outgoing_deck: int, duration_ms: int) -> list[VDJCommand]:
    """Bass swap — kill incoming bass, crossfade 50%, swap bass, finish crossfade."""
    quarter = duration_ms // 4
    return [
        VDJCommand(f"deck {incoming_deck} eq_low 0%", 0),
        VDJCommand(f"deck {incoming_deck} play", 0),
        VDJCommand(f"crossfader 50%", quarter),
        # Bass swap at midpoint
        VDJCommand(f"deck {outgoing_deck} eq_low 0%", quarter * 2),
        VDJCommand(f"deck {incoming_deck} eq_low 100%", quarter * 2),
        VDJCommand(f"crossfader 75%", quarter * 3),
        VDJCommand(f"crossfader 100%", duration_ms),
        VDJCommand(f"deck {outgoing_deck} stop", duration_ms + 500),
        VDJCommand(f"deck {outgoing_deck} eq_low 100%", duration_ms + 600),
    ]


def _build_cut(incoming_deck: int, outgoing_deck: int) -> list[VDJCommand]:
    """Hard cut on beat 1."""
    return [
        VDJCommand(f"deck {incoming_deck} play", 0),
        VDJCommand(f"crossfader 100%", 0),
        VDJCommand(f"deck {outgoing_deck} stop", 100),
    ]


def _build_echo_out(incoming_deck: int, outgoing_deck: int, duration_ms: int) -> list[VDJCommand]:
    """Echo/delay on outgoing → cut to incoming."""
    half = duration_ms // 2
    return [
        VDJCommand(f"deck {outgoing_deck} effect 'echo' on", 0),
        VDJCommand(f"crossfader 50%", half // 2),
        VDJCommand(f"deck {incoming_deck} play", half),
        VDJCommand(f"crossfader 100%", half + (half // 2)),
        VDJCommand(f"deck {outgoing_deck} effect 'echo' off", duration_ms),
        VDJCommand(f"deck {outgoing_deck} stop", duration_ms + 500),
    ]


def _build_filter_sweep(incoming_deck: int, outgoing_deck: int, duration_ms: int) -> list[VDJCommand]:
    """Low-pass filter outgoing → bring in incoming clean."""
    third = duration_ms // 3
    return [
        VDJCommand(f"deck {outgoing_deck} filter_low 80%", 0),
        VDJCommand(f"deck {incoming_deck} play", third),
        VDJCommand(f"crossfader 50%", third),
        VDJCommand(f"deck {outgoing_deck} filter_low 20%", third * 2),
        VDJCommand(f"crossfader 100%", duration_ms),
        VDJCommand(f"deck {outgoing_deck} filter_low 100%", duration_ms + 100),
        VDJCommand(f"deck {outgoing_deck} stop", duration_ms + 500),
    ]


# ---------------------------------------------------------------------------
# Plan builder
# ---------------------------------------------------------------------------

_BUILDERS = {
    TransitionType.BLEND: lambda i, o, d: _build_blend(i, o, d),
    TransitionType.BASS_SWAP: lambda i, o, d: _build_bass_swap(i, o, d),
    TransitionType.CUT: lambda i, o, _d: _build_cut(i, o),
    TransitionType.ECHO_OUT: lambda i, o, d: _build_echo_out(i, o, d),
    TransitionType.FILTER_SWEEP: lambda i, o, d: _build_filter_sweep(i, o, d),
}

# Default duration bars per type
_DURATION_BARS = {
    TransitionType.BLEND: 16,
    TransitionType.BASS_SWAP: 16,
    TransitionType.CUT: 1,
    TransitionType.ECHO_OUT: 8,
    TransitionType.FILTER_SWEEP: 8,
}


def plan(
    current: TrackModel,
    next_track: TrackModel,
    set_state: SetState,
    incoming_deck: int = 2,
    outgoing_deck: int = 1,
    current_position_bars: int = 0,
) -> TransitionPlan:
    """Build a complete transition plan between two tracks."""
    transition_type = select_transition_type(current, next_track, set_state)
    duration_bars = _DURATION_BARS[transition_type]
    start_bar = calculate_start_bar(current_position_bars)
    bpm = current.bpm or next_track.bpm or 128.0

    tp = TransitionPlan(
        transition_type=transition_type,
        start_bar=start_bar,
        duration_bars=duration_bars,
        bpm=bpm,
    )

    builder = _BUILDERS[transition_type]
    tp.commands = builder(incoming_deck, outgoing_deck, tp.duration_ms)

    return tp
