"""Transition planning — type selection, timing, and VDJscript generation."""

from __future__ import annotations

import logging
import math
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
# Vocal detection safety (Step 5.4)
# ---------------------------------------------------------------------------


def has_vocals_near(track: TrackModel, position_ms: int, window_ms: int = 2000) -> bool:
    """Check if the track has vocals near the given position.

    Returns True if any vocal range in ``track.has_vocals_at`` overlaps
    with ``[position_ms - window_ms, position_ms + window_ms]``.
    """
    check_start = position_ms - window_ms
    check_end = position_ms + window_ms
    for vocal_range in track.has_vocals_at:
        if len(vocal_range) < 2:
            continue
        v_start, v_end = vocal_range[0], vocal_range[1]
        # Overlap check: ranges overlap if one starts before the other ends
        if v_start <= check_end and v_end >= check_start:
            return True
    return False


# ---------------------------------------------------------------------------
# Phrase alignment helper (Step 5.3)
# ---------------------------------------------------------------------------


def _align_to_phrase(offset_ms: int, bpm: float, phrase_bars: int = 8) -> int:
    """Snap a timing offset to the nearest phrase boundary.

    Calculates the ms duration of a phrase (phrase_bars bars at the given BPM)
    and rounds offset_ms to the nearest multiple of that phrase duration.
    """
    if bpm <= 0:
        return offset_ms
    ms_per_beat = 60_000 / bpm
    ms_per_bar = ms_per_beat * 4
    phrase_ms = ms_per_bar * phrase_bars
    if phrase_ms <= 0:
        return offset_ms
    return int(round(offset_ms / phrase_ms) * phrase_ms)


# ---------------------------------------------------------------------------
# Transition type selection (Step 5.2 — refined)
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

    # Large BPM jump (>5) or large energy jump outside peak → cut
    if bpm_delta > 5:
        return TransitionType.CUT

    # Genre boundary → echo_out or filter_sweep
    if current.genre and next_track.genre:
        current_genres = set(g.lower() for g in current.genre)
        next_genres = set(g.lower() for g in next_track.genre)
        if not current_genres & next_genres:
            # Prefer echo_out during high energy, filter_sweep otherwise
            if energy_current > 0.7:
                return TransitionType.ECHO_OUT
            return TransitionType.FILTER_SWEEP

    # Energy peak moment (either track energy > 0.8) → bass_swap (most dramatic)
    if (energy_current > 0.8 or energy_next > 0.8) and set_state.phase.value == "peak":
        return TransitionType.BASS_SWAP

    # Big energy delta at peak → bass swap
    if energy_delta > 0.3 and set_state.phase.value == "peak":
        return TransitionType.BASS_SWAP

    # Small BPM jump (3-5) → bass swap with pitch ride
    if 3 <= bpm_delta <= 5:
        return TransitionType.BASS_SWAP

    # Same BPM (±2), compatible key → blend or bass_swap
    if bpm_delta <= 2 and current.key and next_track.key:
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
    """Build a complete transition plan between two tracks.

    Incorporates vocal detection safety: if the transition start falls during
    a vocal phrase on the outgoing track, the transition type is overridden to
    bass_swap to preserve vocal clarity.
    """
    transition_type = select_transition_type(current, next_track, set_state)
    duration_bars = _DURATION_BARS[transition_type]
    start_bar = calculate_start_bar(current_position_bars)
    bpm = current.bpm or next_track.bpm or 128.0

    # Calculate the transition start position in ms for vocal check
    if bpm > 0:
        ms_per_bar = (60_000 / bpm) * 4
        start_position_ms = int(start_bar * ms_per_bar)

        # Vocal safety: if transition starts during vocals, prefer bass_swap
        if has_vocals_near(current, start_position_ms):
            if transition_type not in (TransitionType.BASS_SWAP, TransitionType.CUT):
                logger.info(
                    "Vocal phrase detected at transition start (%d ms); "
                    "switching from %s to bass_swap for vocal clarity",
                    start_position_ms,
                    transition_type.value,
                )
                transition_type = TransitionType.BASS_SWAP
                duration_bars = _DURATION_BARS[transition_type]

    tp = TransitionPlan(
        transition_type=transition_type,
        start_bar=start_bar,
        duration_bars=duration_bars,
        bpm=bpm,
    )

    builder = _BUILDERS[transition_type]
    commands = builder(incoming_deck, outgoing_deck, tp.duration_ms)

    # Align command offsets to phrase boundaries for timing precision (Step 5.3)
    aligned_commands: list[VDJCommand] = []
    for cmd in commands:
        # Only align intermediate commands, not start (0) or small cleanup offsets
        if cmd.offset_ms > 0 and cmd.offset_ms < tp.duration_ms:
            aligned_offset = _align_to_phrase(cmd.offset_ms, bpm, phrase_bars=8)
            # Keep aligned offset within bounds and don't let it exceed duration
            if aligned_offset >= tp.duration_ms:
                aligned_offset = cmd.offset_ms  # fall back to original
            aligned_commands.append(VDJCommand(cmd.script, aligned_offset))
        else:
            aligned_commands.append(cmd)
    tp.commands = aligned_commands

    return tp
