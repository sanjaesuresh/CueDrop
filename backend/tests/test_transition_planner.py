"""Tests for transition planner."""

from __future__ import annotations

import pytest

from backend.models import Phase, SetState, TrackModel, TransitionType
from backend.transition_planner import (
    TransitionPlan,
    VDJCommand,
    calculate_start_bar,
    plan,
    select_transition_type,
)


def _track(bpm=126.0, key="8A", energy=0.5, genre=None) -> TrackModel:
    return TrackModel(
        title="T", artist="A", bpm=bpm, key=key, energy=energy,
        genre=genre or ["tech house"],
    )


# ---------------------------------------------------------------------------
# select_transition_type
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
        result = select_transition_type(
            _track(genre=["tech house"]),
            _track(genre=["drum and bass"]),
            SetState(),
        )
        assert result == TransitionType.FILTER_SWEEP

    def test_big_energy_at_peak_bass_swap(self):
        result = select_transition_type(
            _track(energy=0.4, bpm=126),
            _track(energy=0.9, bpm=126),
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
# VDJCommand
# ---------------------------------------------------------------------------


def test_vdj_command():
    cmd = VDJCommand("deck 1 play", offset_ms=500)
    assert cmd.script == "deck 1 play"
    assert cmd.offset_ms == 500
