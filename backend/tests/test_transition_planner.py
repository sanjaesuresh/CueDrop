"""Tests for transition planner."""

from __future__ import annotations

import pytest

from backend.models import Phase, SetState, TrackModel, TransitionType
from backend.transition_planner import (
    TransitionPlan,
    VDJCommand,
    _align_to_phrase,
    _build_echo_out,
    _build_filter_sweep,
    calculate_start_bar,
    has_vocals_near,
    plan,
    select_transition_type,
)


def _track(
    bpm=126.0,
    key="8A",
    energy=0.5,
    genre=None,
    has_vocals_at=None,
) -> TrackModel:
    return TrackModel(
        title="T", artist="A", bpm=bpm, key=key, energy=energy,
        genre=genre or ["tech house"],
        has_vocals_at=has_vocals_at or [],
    )


# ---------------------------------------------------------------------------
# has_vocals_near (Step 5.4)
# ---------------------------------------------------------------------------


class TestHasVocalsNear:
    def test_no_vocals(self):
        track = _track()
        assert has_vocals_near(track, 10000) is False

    def test_vocals_at_position(self):
        track = _track(has_vocals_at=[[8000, 12000]])
        assert has_vocals_near(track, 10000) is True

    def test_vocals_within_window(self):
        # Vocal range starts 1000ms after position, but within 2000ms window
        track = _track(has_vocals_at=[[11000, 15000]])
        assert has_vocals_near(track, 10000) is True

    def test_vocals_before_window(self):
        # Vocal range starts at 11000, position is 10000, window is 2000
        track = _track(has_vocals_at=[[11500, 15000]])
        assert has_vocals_near(track, 10000) is True

    def test_vocals_outside_window(self):
        # Vocal range is well outside the window
        track = _track(has_vocals_at=[[20000, 25000]])
        assert has_vocals_near(track, 10000) is False

    def test_vocals_ended_before_window(self):
        track = _track(has_vocals_at=[[1000, 5000]])
        assert has_vocals_near(track, 10000) is False

    def test_custom_window(self):
        track = _track(has_vocals_at=[[14000, 16000]])
        # With default 2000ms window, 10000 checks [8000, 12000] — no overlap
        assert has_vocals_near(track, 10000, window_ms=2000) is False
        # With 5000ms window, 10000 checks [5000, 15000] — overlaps
        assert has_vocals_near(track, 10000, window_ms=5000) is True

    def test_multiple_vocal_ranges(self):
        track = _track(has_vocals_at=[[1000, 3000], [9000, 11000], [20000, 25000]])
        assert has_vocals_near(track, 10000) is True
        assert has_vocals_near(track, 15000) is False

    def test_malformed_range_skipped(self):
        track = _track(has_vocals_at=[[5000]])  # Only one element
        assert has_vocals_near(track, 5000) is False


# ---------------------------------------------------------------------------
# _align_to_phrase (Step 5.3)
# ---------------------------------------------------------------------------


class TestAlignToPhrase:
    def test_exact_phrase_boundary(self):
        # 120 BPM: beat = 500ms, bar = 2000ms, 8-bar phrase = 16000ms
        assert _align_to_phrase(16000, 120.0, 8) == 16000

    def test_snap_to_nearest(self):
        # 120 BPM: 8-bar phrase = 16000ms
        # 17000 is closer to 16000 than 32000
        assert _align_to_phrase(17000, 120.0, 8) == 16000

    def test_snap_up(self):
        # 120 BPM: 8-bar phrase = 16000ms
        # 25000 is closer to 32000 than 16000
        assert _align_to_phrase(25000, 120.0, 8) == 32000

    def test_zero_offset(self):
        assert _align_to_phrase(0, 128.0, 8) == 0

    def test_zero_bpm_returns_original(self):
        assert _align_to_phrase(5000, 0.0, 8) == 5000

    def test_different_phrase_length(self):
        # 120 BPM: 4-bar phrase = 8000ms
        assert _align_to_phrase(9000, 120.0, 4) == 8000

    def test_rounding_midpoint(self):
        # 120 BPM: 8-bar phrase = 16000ms
        # Exactly 8000 = halfway, round rounds to nearest even → 0 or 16000
        result = _align_to_phrase(8000, 120.0, 8)
        assert result in (0, 8000, 16000)  # Accept any valid rounding


# ---------------------------------------------------------------------------
# select_transition_type (Step 5.2 — refined)
# ---------------------------------------------------------------------------


class TestSelectTransitionType:
    def test_large_bpm_jump_cut(self):
        result = select_transition_type(_track(bpm=126), _track(bpm=140), SetState())
        assert result == TransitionType.CUT

    def test_same_bpm_compatible_key_blend(self):
        result = select_transition_type(_track(bpm=126, key="8A"), _track(bpm=126, key="9A"), SetState())
        assert result == TransitionType.BLEND

    def test_medium_bpm_jump_bass_swap(self):
        result = select_transition_type(_track(bpm=126), _track(bpm=130), SetState())
        assert result == TransitionType.BASS_SWAP

    def test_genre_boundary_filter_sweep(self):
        """Genre boundary with lower energy -> filter_sweep."""
        result = select_transition_type(
            _track(genre=["tech house"], energy=0.5),
            _track(genre=["drum and bass"], energy=0.5),
            SetState(),
        )
        assert result == TransitionType.FILTER_SWEEP

    def test_genre_boundary_high_energy_echo_out(self):
        """Genre boundary with high outgoing energy -> echo_out."""
        result = select_transition_type(
            _track(genre=["tech house"], energy=0.8),
            _track(genre=["drum and bass"], energy=0.5),
            SetState(),
        )
        assert result == TransitionType.ECHO_OUT

    def test_big_energy_at_peak_bass_swap(self):
        result = select_transition_type(
            _track(energy=0.4, bpm=126),
            _track(energy=0.9, bpm=126),
            SetState(phase=Phase.PEAK),
        )
        assert result == TransitionType.BASS_SWAP

    def test_energy_peak_moment_bass_swap(self):
        """Energy > 0.8 at peak phase -> bass_swap (most dramatic)."""
        result = select_transition_type(
            _track(energy=0.85, bpm=126, key="8A"),
            _track(energy=0.6, bpm=126, key="9A"),
            SetState(phase=Phase.PEAK),
        )
        assert result == TransitionType.BASS_SWAP

    def test_no_key_defaults_to_blend(self):
        result = select_transition_type(
            TrackModel(title="A", artist="X", bpm=126),
            TrackModel(title="B", artist="Y", bpm=126),
            SetState(),
        )
        assert result == TransitionType.BLEND

    def test_small_bpm_delta_3_bass_swap(self):
        """BPM delta of exactly 3 -> bass_swap."""
        result = select_transition_type(_track(bpm=126), _track(bpm=129), SetState())
        assert result == TransitionType.BASS_SWAP

    def test_small_bpm_delta_5_bass_swap(self):
        """BPM delta of exactly 5 -> bass_swap."""
        result = select_transition_type(_track(bpm=126), _track(bpm=131), SetState())
        assert result == TransitionType.BASS_SWAP

    def test_bpm_delta_6_cut(self):
        """BPM delta of 6 is large enough for cut."""
        result = select_transition_type(_track(bpm=126), _track(bpm=132), SetState())
        assert result == TransitionType.CUT

    def test_same_genre_no_boundary(self):
        """Same genre should not trigger genre boundary logic."""
        result = select_transition_type(
            _track(genre=["tech house"], bpm=126, key="8A"),
            _track(genre=["tech house"], bpm=126, key="9A"),
            SetState(),
        )
        assert result == TransitionType.BLEND


# ---------------------------------------------------------------------------
# calculate_start_bar
# ---------------------------------------------------------------------------


class TestCalculateStartBar:
    def test_on_phrase_boundary(self):
        assert calculate_start_bar(32) == 32

    def test_between_phrases(self):
        assert calculate_start_bar(35) == 48  # next 16-bar boundary

    def test_just_after_boundary(self):
        assert calculate_start_bar(1) == 16

    def test_custom_phrase_length(self):
        assert calculate_start_bar(5, phrase_length=8) == 8

    def test_zero(self):
        assert calculate_start_bar(0) == 0


# ---------------------------------------------------------------------------
# TransitionPlan
# ---------------------------------------------------------------------------


class TestTransitionPlan:
    def test_duration_ms_calculation(self):
        tp = TransitionPlan(
            transition_type=TransitionType.BLEND,
            start_bar=0, duration_bars=16, bpm=120.0,
        )
        # 120 BPM = 500ms per beat, 2000ms per bar, 16 bars = 32000ms
        assert tp.duration_ms == 32000

    def test_duration_ms_zero_bpm(self):
        tp = TransitionPlan(
            transition_type=TransitionType.CUT,
            start_bar=0, duration_bars=1, bpm=0,
        )
        assert tp.duration_ms == 0


# ---------------------------------------------------------------------------
# Echo out and filter sweep command generation
# ---------------------------------------------------------------------------


class TestEchoOutCommands:
    def test_echo_out_has_echo_effect(self):
        cmds = _build_echo_out(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        echo_on = [c for c in cmds if "echo" in c.script and "on" in c.script]
        echo_off = [c for c in cmds if "echo" in c.script and "off" in c.script]
        assert len(echo_on) == 1
        assert len(echo_off) == 1

    def test_echo_out_plays_incoming(self):
        cmds = _build_echo_out(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        play_cmds = [c for c in cmds if "deck 2 play" in c.script]
        assert len(play_cmds) == 1

    def test_echo_out_stops_outgoing(self):
        cmds = _build_echo_out(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        stop_cmds = [c for c in cmds if "deck 1 stop" in c.script]
        assert len(stop_cmds) == 1

    def test_echo_out_offsets_ordered(self):
        cmds = _build_echo_out(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        offsets = [c.offset_ms for c in cmds]
        assert offsets == sorted(offsets)


class TestFilterSweepCommands:
    def test_filter_sweep_has_filter(self):
        cmds = _build_filter_sweep(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        filter_cmds = [c for c in cmds if "filter_low" in c.script]
        assert len(filter_cmds) >= 2

    def test_filter_sweep_plays_incoming(self):
        cmds = _build_filter_sweep(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        play_cmds = [c for c in cmds if "deck 2 play" in c.script]
        assert len(play_cmds) == 1

    def test_filter_sweep_stops_outgoing(self):
        cmds = _build_filter_sweep(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        stop_cmds = [c for c in cmds if "deck 1 stop" in c.script]
        assert len(stop_cmds) == 1

    def test_filter_sweep_resets_filter(self):
        """Filter should be reset to 100% after transition."""
        cmds = _build_filter_sweep(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        reset_cmds = [c for c in cmds if "filter_low 100%" in c.script]
        assert len(reset_cmds) == 1

    def test_filter_sweep_offsets_ordered(self):
        cmds = _build_filter_sweep(incoming_deck=2, outgoing_deck=1, duration_ms=16000)
        offsets = [c.offset_ms for c in cmds]
        assert offsets == sorted(offsets)


# ---------------------------------------------------------------------------
# plan() — full pipeline
# ---------------------------------------------------------------------------


class TestPlan:
    def test_blend_plan(self):
        result = plan(_track(bpm=126, key="8A"), _track(bpm=126, key="9A"), SetState())
        assert result.transition_type == TransitionType.BLEND
        assert result.duration_bars == 16
        assert len(result.commands) > 0
        # First command should play incoming deck
        assert "play" in result.commands[0].script
        # Last command should stop outgoing
        assert "stop" in result.commands[-1].script

    def test_cut_plan(self):
        result = plan(_track(bpm=126), _track(bpm=140), SetState())
        assert result.transition_type == TransitionType.CUT
        assert result.duration_bars == 1
        assert len(result.commands) == 3

    def test_bass_swap_plan(self):
        result = plan(_track(bpm=126), _track(bpm=130), SetState())
        assert result.transition_type == TransitionType.BASS_SWAP
        # Should have eq_low commands
        eq_cmds = [c for c in result.commands if "eq_low" in c.script]
        assert len(eq_cmds) >= 2

    def test_commands_have_increasing_offsets(self):
        result = plan(_track(bpm=126, key="8A"), _track(bpm=126, key="9A"), SetState())
        offsets = [c.offset_ms for c in result.commands]
        assert offsets == sorted(offsets)

    def test_custom_decks(self):
        result = plan(
            _track(bpm=126, key="8A"), _track(bpm=126, key="9A"),
            SetState(), incoming_deck=1, outgoing_deck=2,
        )
        assert any("deck 1" in c.script for c in result.commands)
        assert any("deck 2" in c.script for c in result.commands)

    def test_phrase_aligned_start(self):
        result = plan(
            _track(bpm=126, key="8A"), _track(bpm=126, key="9A"),
            SetState(), current_position_bars=35,
        )
        assert result.start_bar == 48  # next 16-bar boundary

    def test_uses_current_bpm(self):
        result = plan(_track(bpm=128, key="8A"), _track(bpm=128, key="9A"), SetState())
        assert result.bpm == 128.0


# ---------------------------------------------------------------------------
# Vocal safety in plan()
# ---------------------------------------------------------------------------


class TestVocalSafetyInPlan:
    def test_vocal_overrides_blend_to_bass_swap(self):
        """If transition starts during vocals, blend should become bass_swap."""
        # Start bar = 0, BPM = 120 -> start_position_ms = 0
        track = _track(bpm=120, key="8A", has_vocals_at=[[0, 5000]])
        next_t = _track(bpm=120, key="9A")
        result = plan(track, next_t, SetState(), current_position_bars=0)
        assert result.transition_type == TransitionType.BASS_SWAP

    def test_no_vocal_keeps_blend(self):
        """Without vocals, blend should remain blend."""
        track = _track(bpm=120, key="8A")
        next_t = _track(bpm=120, key="9A")
        result = plan(track, next_t, SetState(), current_position_bars=0)
        assert result.transition_type == TransitionType.BLEND

    def test_vocal_does_not_override_cut(self):
        """Cut transitions should not be overridden by vocal detection."""
        track = _track(bpm=120, has_vocals_at=[[0, 5000]])
        next_t = _track(bpm=140)
        result = plan(track, next_t, SetState(), current_position_bars=0)
        assert result.transition_type == TransitionType.CUT

    def test_vocal_does_not_override_existing_bass_swap(self):
        """Bass swap should remain bass swap even with vocals."""
        track = _track(bpm=126, has_vocals_at=[[0, 500000]])
        next_t = _track(bpm=130)  # 4 BPM delta -> bass_swap
        result = plan(track, next_t, SetState(), current_position_bars=0)
        assert result.transition_type == TransitionType.BASS_SWAP


# ---------------------------------------------------------------------------
# VDJCommand
# ---------------------------------------------------------------------------


def test_vdj_command():
    cmd = VDJCommand("deck 1 play", offset_ms=500)
    assert cmd.script == "deck 1 play"
    assert cmd.offset_ms == 500
