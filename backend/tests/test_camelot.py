"""Tests for Camelot wheel logic."""

from __future__ import annotations

import pytest

from backend.camelot import (
    _normalize,
    compatibility_score,
    get_compatible_keys,
    is_compatible,
)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_camelot_code_passthrough(self):
        assert _normalize("8A") == "8A"
        assert _normalize("12B") == "12B"

    def test_camelot_case_insensitive(self):
        assert _normalize("8a") == "8A"
        assert _normalize("12b") == "12B"

    def test_standard_major(self):
        assert _normalize("C") == "8B"
        assert _normalize("G") == "9B"
        assert _normalize("D") == "10B"

    def test_standard_minor(self):
        assert _normalize("Am") == "8A"
        assert _normalize("Em") == "9A"
        assert _normalize("Dm") == "7A"

    def test_sharps(self):
        assert _normalize("F#") == "2B"
        assert _normalize("C#m") == "12A"

    def test_flats(self):
        assert _normalize("Bb") == "6B"
        assert _normalize("Ebm") == "2A"

    def test_enharmonic_equivalents(self):
        assert _normalize("C#") == _normalize("Db")
        assert _normalize("G#m") == _normalize("Abm")

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown key"):
            _normalize("X#m")

    def test_whitespace_stripped(self):
        assert _normalize("  8A  ") == "8A"
        assert _normalize(" Am ") == "8A"


# ---------------------------------------------------------------------------
# get_compatible_keys
# ---------------------------------------------------------------------------


class TestGetCompatibleKeys:
    def test_returns_four_keys(self):
        result = get_compatible_keys("8A")
        assert len(result) == 4

    def test_includes_self(self):
        result = get_compatible_keys("8A")
        assert "8A" in result

    def test_includes_plus_one(self):
        result = get_compatible_keys("8A")
        assert "9A" in result

    def test_includes_minus_one(self):
        result = get_compatible_keys("8A")
        assert "7A" in result

    def test_includes_mode_switch(self):
        result = get_compatible_keys("8A")
        assert "8B" in result

    def test_wraps_around_12_to_1(self):
        result = get_compatible_keys("12A")
        assert "1A" in result
        assert "11A" in result

    def test_wraps_around_1_to_12(self):
        result = get_compatible_keys("1A")
        assert "12A" in result
        assert "2A" in result

    def test_accepts_standard_key(self):
        result = get_compatible_keys("Am")  # = 8A
        assert "8A" in result
        assert "9A" in result

    def test_b_mode_switch(self):
        result = get_compatible_keys("8B")
        assert "8A" in result
        assert "9B" in result
        assert "7B" in result


# ---------------------------------------------------------------------------
# is_compatible
# ---------------------------------------------------------------------------


class TestIsCompatible:
    def test_same_key(self):
        assert is_compatible("8A", "8A") is True

    def test_adjacent_plus(self):
        assert is_compatible("8A", "9A") is True

    def test_adjacent_minus(self):
        assert is_compatible("8A", "7A") is True

    def test_mode_switch(self):
        assert is_compatible("8A", "8B") is True

    def test_incompatible(self):
        assert is_compatible("8A", "3A") is False

    def test_two_steps_incompatible(self):
        assert is_compatible("8A", "10A") is False

    def test_standard_keys(self):
        assert is_compatible("Am", "C") is True  # 8A ↔ 8B (mode switch)

    def test_cross_mode_adjacent_incompatible(self):
        assert is_compatible("8A", "9B") is False


# ---------------------------------------------------------------------------
# compatibility_score
# ---------------------------------------------------------------------------


class TestCompatibilityScore:
    def test_same_key_is_1(self):
        assert compatibility_score("8A", "8A") == 1.0

    def test_adjacent_is_075(self):
        assert compatibility_score("8A", "9A") == 0.75
        assert compatibility_score("8A", "7A") == 0.75

    def test_mode_switch_is_075(self):
        assert compatibility_score("8A", "8B") == 0.75

    def test_two_steps_same_mode_is_025(self):
        assert compatibility_score("8A", "10A") == 0.25
        assert compatibility_score("8A", "6A") == 0.25

    def test_one_step_cross_mode_is_025(self):
        assert compatibility_score("8A", "9B") == 0.25
        assert compatibility_score("8A", "7B") == 0.25

    def test_far_apart_is_0(self):
        assert compatibility_score("8A", "3A") == 0.0
        assert compatibility_score("1A", "7A") == 0.0

    def test_standard_key_input(self):
        assert compatibility_score("Am", "Em") == 0.75  # 8A → 9A

    def test_symmetry(self):
        assert compatibility_score("8A", "9A") == compatibility_score("9A", "8A")
        assert compatibility_score("8A", "8B") == compatibility_score("8B", "8A")

    def test_wrap_around_scoring(self):
        assert compatibility_score("12A", "1A") == 0.75
        assert compatibility_score("1A", "12A") == 0.75
