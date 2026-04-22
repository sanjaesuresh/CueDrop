"""Comprehensive tests for CueDrop Pydantic models."""

import pytest
from pydantic import ValidationError

from backend.models import DJModel, SetImport, SetModel, TrackModel, generate_track_id


# ---------------------------------------------------------------------------
# generate_track_id unit tests
# ---------------------------------------------------------------------------


class TestGenerateTrackId:
    """Tests for the generate_track_id helper function."""

    def test_basic_original(self):
        result = generate_track_id("Artist", "Title", None)
        assert result == "artist::title::original"

    def test_basic_with_remix(self):
        result = generate_track_id("Artist", "Title", "Extended Mix")
        assert result == "artist::title::extended mix"

    def test_lowercases_all_parts(self):
        result = generate_track_id("DEADMAU5", "STROBE", "ORIGINAL MIX")
        assert result == "deadmau5::strobe::original mix"

    def test_special_chars_replaced_with_space(self):
        # Hyphens, dots, parentheses, commas become spaces; whitespace is then collapsed
        result = generate_track_id("Flume", "Say It (feat. Tove Lo)", None)
        # "(", ".", ")" each become a space; adjacent spaces collapse to single space
        assert result == "flume::say it feat tove lo::original"

    def test_special_chars_whitespace_collapsed(self):
        # Multiple spaces from special char replacement should collapse
        result = generate_track_id("A&B", "X---Y", None)
        assert result == "a b::x y::original"

    def test_leading_trailing_whitespace_stripped(self):
        result = generate_track_id("  Artist  ", "  Title  ", None)
        assert result == "artist::title::original"

    def test_leading_trailing_special_chars_stripped(self):
        # Leading/trailing non-alphanumeric become spaces which then get stripped
        result = generate_track_id("-Artist-", "-Title-", None)
        assert result == "artist::title::original"

    def test_remix_none_becomes_original(self):
        result = generate_track_id("X", "Y", None)
        assert result.endswith("::original")

    def test_remix_empty_string_becomes_original(self):
        # Empty string is falsy, so "original" should be used
        result = generate_track_id("X", "Y", "")
        assert result.endswith("::original")

    def test_colons_in_input_become_spaces(self):
        # Colons in the input data must NOT bleed into the separator
        result = generate_track_id("Artist: Remix", "Title: Subtitle", None)
        # colons are non-alphanumeric (not \s), so they become spaces
        assert "::" in result
        parts = result.split("::")
        assert len(parts) == 3
        # The colon in the artist/title became a space
        assert "artist  remix" == parts[0] or "artist remix" == parts[0]

    def test_numbers_preserved(self):
        result = generate_track_id("808 State", "Pacific 202", None)
        assert result == "808 state::pacific 202::original"

    def test_separator_always_double_colon(self):
        result = generate_track_id("a", "b", "c")
        parts = result.split("::")
        assert len(parts) == 3

    def test_unicode_non_ascii_replaced(self):
        # Non-ASCII characters are non-alphanumeric and should be replaced
        result = generate_track_id("Björk", "Jóga", None)
        parts = result.split("::")
        # Non-ASCII chars become spaces; result should have no non-ASCII
        assert all(ord(c) < 128 for c in result)
        assert len(parts) == 3


# ---------------------------------------------------------------------------
# TrackModel tests
# ---------------------------------------------------------------------------


class TestTrackModel:
    """Tests for TrackModel field definitions and auto-generation."""

    def test_minimal_creation(self):
        track = TrackModel(title="Strobe", artist="deadmau5")
        assert track.title == "Strobe"
        assert track.artist == "deadmau5"

    def test_track_id_auto_generated_when_absent(self):
        track = TrackModel(title="Strobe", artist="deadmau5")
        assert track.track_id is not None
        assert track.track_id == "deadmau5::strobe::original"

    def test_track_id_auto_generated_with_remix(self):
        track = TrackModel(title="Strobe", artist="deadmau5", remix="Original Mix")
        assert track.track_id == "deadmau5::strobe::original mix"

    def test_track_id_preserved_when_provided(self):
        custom_id = "my-custom-id"
        track = TrackModel(title="Strobe", artist="deadmau5", track_id=custom_id)
        assert track.track_id == custom_id

    def test_track_id_preserved_when_provided_with_remix(self):
        custom_id = "explicit-id-123"
        track = TrackModel(
            title="Strobe", artist="deadmau5", remix="Remix", track_id=custom_id
        )
        assert track.track_id == custom_id

    def test_required_fields_title_missing_raises(self):
        with pytest.raises(ValidationError):
            TrackModel(artist="deadmau5")  # type: ignore[call-arg]

    def test_required_fields_artist_missing_raises(self):
        with pytest.raises(ValidationError):
            TrackModel(title="Strobe")  # type: ignore[call-arg]

    def test_optional_fields_default_to_none(self):
        track = TrackModel(title="T", artist="A")
        assert track.remix is None
        assert track.bpm is None
        assert track.key is None
        assert track.energy is None
        assert track.intro_bars is None
        assert track.outro_bars is None
        assert track.duration_ms is None
        assert track.label is None
        assert track.has_dj_edit is None
        assert track.dj_edit_bpm is None

    def test_genre_defaults_to_empty_list(self):
        track = TrackModel(title="T", artist="A")
        assert track.genre == []

    def test_all_fields_accepted(self):
        track = TrackModel(
            track_id="custom",
            title="Say It",
            artist="Flume",
            remix="Extended",
            bpm=128.0,
            key="8A",
            energy=7.5,
            genre=["Electronic", "Future Bass"],
            intro_bars=8,
            outro_bars=4,
            duration_ms=360000,
            label="Future Classic",
            has_dj_edit=True,
            dj_edit_bpm=130.0,
        )
        assert track.bpm == 128.0
        assert track.energy == 7.5
        assert track.genre == ["Electronic", "Future Bass"]
        assert track.has_dj_edit is True
        assert track.dj_edit_bpm == 130.0

    def test_bpm_accepts_float(self):
        track = TrackModel(title="T", artist="A", bpm=128.5)
        assert track.bpm == 128.5

    def test_energy_accepts_float(self):
        track = TrackModel(title="T", artist="A", energy=9.1)
        assert track.energy == 9.1

    def test_track_id_normalization_special_chars(self):
        track = TrackModel(title="Say It (feat. Tove Lo)", artist="Flume")
        # Special chars become spaces, whitespace collapsed
        assert "::" in track.track_id
        parts = track.track_id.split("::")
        assert parts[0] == "flume"
        assert parts[2] == "original"
        # Parentheses and dot become spaces, should be collapsed
        assert "  " not in parts[1]  # no double spaces

    def test_track_id_normalization_uppercase(self):
        track = TrackModel(title="STROBE", artist="DEADMAU5")
        assert track.track_id == "deadmau5::strobe::original"

    def test_track_id_normalization_mixed_case_remix(self):
        track = TrackModel(title="strobe", artist="deadmau5", remix="ORIGINAL MIX")
        assert track.track_id == "deadmau5::strobe::original mix"


# ---------------------------------------------------------------------------
# DJModel tests
# ---------------------------------------------------------------------------


class TestDJModel:
    """Tests for DJModel field definitions."""

    def test_minimal_creation(self):
        dj = DJModel(name="DJ Snake")
        assert dj.name == "DJ Snake"

    def test_required_name_missing_raises(self):
        with pytest.raises(ValidationError):
            DJModel()  # type: ignore[call-arg]

    def test_genres_defaults_to_empty_list(self):
        dj = DJModel(name="X")
        assert dj.genres == []

    def test_profile_url_defaults_to_none(self):
        dj = DJModel(name="X")
        assert dj.profile_url is None

    def test_set_count_defaults_to_zero(self):
        dj = DJModel(name="X")
        assert dj.set_count == 0

    def test_all_fields_accepted(self):
        dj = DJModel(
            name="DJ Snake",
            genres=["Trap", "EDM"],
            profile_url="https://djsnake.com",
            set_count=42,
        )
        assert dj.genres == ["Trap", "EDM"]
        assert dj.profile_url == "https://djsnake.com"
        assert dj.set_count == 42


# ---------------------------------------------------------------------------
# SetModel tests
# ---------------------------------------------------------------------------


class TestSetModel:
    """Tests for SetModel field definitions and set_id auto-generation."""

    def test_minimal_creation(self):
        s = SetModel(dj_name="deadmau5")
        assert s.dj_name == "deadmau5"

    def test_required_dj_name_missing_raises(self):
        with pytest.raises(ValidationError):
            SetModel()  # type: ignore[call-arg]

    def test_set_id_auto_generated_when_absent(self):
        s = SetModel(dj_name="deadmau5")
        assert s.set_id is not None
        assert len(s.set_id) == 12
        assert s.set_id.isalnum()

    def test_set_id_preserved_when_provided(self):
        s = SetModel(dj_name="deadmau5", set_id="my-set-id-123")
        assert s.set_id == "my-set-id-123"

    def test_set_id_unique_per_instance(self):
        s1 = SetModel(dj_name="A")
        s2 = SetModel(dj_name="B")
        assert s1.set_id != s2.set_id

    def test_optional_fields_default_to_none(self):
        s = SetModel(dj_name="A")
        assert s.event is None
        assert s.date is None
        assert s.venue is None
        assert s.source_url is None
        assert s.track_count is None

    def test_all_optional_fields_accepted(self):
        s = SetModel(
            dj_name="deadmau5",
            event="EDC Las Vegas",
            date="2024-05-17",
            venue="Circuit Grounds",
            source_url="https://youtube.com/watch?v=xxx",
            track_count=20,
        )
        assert s.event == "EDC Las Vegas"
        assert s.date == "2024-05-17"
        assert s.venue == "Circuit Grounds"
        assert s.source_url == "https://youtube.com/watch?v=xxx"
        assert s.track_count == 20

    def test_set_id_is_hex_string(self):
        s = SetModel(dj_name="X")
        # uuid4().hex[:12] should only contain hex characters
        assert all(c in "0123456789abcdef" for c in s.set_id)


# ---------------------------------------------------------------------------
# SetImport tests
# ---------------------------------------------------------------------------


class TestSetImport:
    """Tests for SetImport, including DJModel string coercion."""

    def _make_track(self, title="Track 1", artist="Artist 1"):
        return TrackModel(title=title, artist=artist)

    def test_dj_string_coerced_to_djmodel(self):
        si = SetImport(dj="deadmau5", tracks=[self._make_track()])
        assert isinstance(si.dj, DJModel)
        assert si.dj.name == "deadmau5"

    def test_dj_djmodel_accepted_as_is(self):
        dj = DJModel(name="deadmau5", genres=["Techno"], set_count=5)
        si = SetImport(dj=dj, tracks=[self._make_track()])
        assert isinstance(si.dj, DJModel)
        assert si.dj.name == "deadmau5"
        assert si.dj.genres == ["Techno"]
        assert si.dj.set_count == 5

    def test_dj_string_coercion_sets_default_genres(self):
        si = SetImport(dj="Some DJ", tracks=[self._make_track()])
        assert si.dj.genres == []
        assert si.dj.set_count == 0
        assert si.dj.profile_url is None

    def test_tracks_required(self):
        with pytest.raises(ValidationError):
            SetImport(dj="X")  # type: ignore[call-arg]

    def test_dj_required(self):
        with pytest.raises(ValidationError):
            SetImport(tracks=[self._make_track()])  # type: ignore[call-arg]

    def test_empty_tracks_list_accepted(self):
        si = SetImport(dj="X", tracks=[])
        assert si.tracks == []

    def test_multiple_tracks_accepted(self):
        tracks = [self._make_track(f"Track {i}", "Artist") for i in range(5)]
        si = SetImport(dj="X", tracks=tracks)
        assert len(si.tracks) == 5

    def test_optional_fields_default_to_none(self):
        si = SetImport(dj="X", tracks=[])
        assert si.event is None
        assert si.date is None
        assert si.venue is None
        assert si.source_url is None

    def test_all_optional_fields_accepted(self):
        si = SetImport(
            dj="DJ Snake",
            event="Ultra Miami",
            date="2024-03-22",
            venue="Mainstage",
            source_url="https://soundcloud.com/djsnake/ultra2024",
            tracks=[self._make_track()],
        )
        assert si.event == "Ultra Miami"
        assert si.date == "2024-03-22"
        assert si.venue == "Mainstage"
        assert si.source_url == "https://soundcloud.com/djsnake/ultra2024"

    def test_tracks_contain_track_models(self):
        raw = {"title": "Lean On", "artist": "Major Lazer"}
        si = SetImport(dj="X", tracks=[raw])  # type: ignore[list-item]
        assert isinstance(si.tracks[0], TrackModel)
        assert si.tracks[0].title == "Lean On"

    def test_track_ids_auto_generated_in_set_import(self):
        si = SetImport(
            dj="X",
            tracks=[TrackModel(title="Strobe", artist="deadmau5")],
        )
        assert si.tracks[0].track_id == "deadmau5::strobe::original"

    def test_dj_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            SetImport(dj=123, tracks=[])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Edge case / normalization tests
# ---------------------------------------------------------------------------


class TestNormalizationEdgeCases:
    """Additional edge cases for track_id normalization."""

    def test_all_special_chars_artist(self):
        # Artist made entirely of special chars → collapses to empty after strip
        track = TrackModel(title="Normal", artist="!@#$%")
        parts = track.track_id.split("::")
        # Should be empty string or whitespace-stripped
        assert parts[0] == ""

    def test_artist_with_ampersand(self):
        track = TrackModel(title="Together", artist="Above & Beyond")
        parts = track.track_id.split("::")
        assert parts[0] == "above beyond"

    def test_title_with_parenthetical_remix(self):
        # Common DJ track format: "Title (Extended Mix)"
        track = TrackModel(title="Clarity (Extended Mix)", artist="Zedd")
        parts = track.track_id.split("::")
        assert parts[0] == "zedd"
        assert "clarity" in parts[1]
        assert "extended mix" in parts[1]
        assert "  " not in parts[1]  # No double spaces

    def test_remix_field_none_vs_original_in_track_id(self):
        t1 = TrackModel(title="X", artist="Y", remix=None)
        t2 = TrackModel(title="X", artist="Y", remix="original")
        # Both should resolve to "original" in the track_id
        assert t1.track_id == t2.track_id

    def test_whitespace_only_remix_treated_as_original(self):
        # Whitespace-only string is truthy, so it won't be replaced by "original"
        # but after normalization it becomes empty-ish
        track = TrackModel(title="X", artist="Y", remix="   ")
        parts = track.track_id.split("::")
        # "   " lowercased = "   ", no special chars replaced, strip = ""
        assert parts[2] == ""

    def test_track_id_consistency_idempotent(self):
        # Generating the same track twice should produce the same id
        t1 = TrackModel(title="Strobe", artist="deadmau5")
        t2 = TrackModel(title="Strobe", artist="deadmau5")
        assert t1.track_id == t2.track_id

    def test_track_id_case_insensitive(self):
        t1 = TrackModel(title="STROBE", artist="DEADMAU5")
        t2 = TrackModel(title="strobe", artist="deadmau5")
        assert t1.track_id == t2.track_id

    def test_set_id_format_uuid_hex_12chars(self):
        # set_id should be exactly 12 hex characters
        s = SetModel(dj_name="X")
        assert len(s.set_id) == 12
        int(s.set_id, 16)  # Raises ValueError if not valid hex

    def test_djmodel_string_coercion_preserves_name_exactly(self):
        # DJ names with spaces and caps should be preserved (no normalization)
        si = SetImport(dj="DJ Snake ft. Ozuna", tracks=[])
        assert si.dj.name == "DJ Snake ft. Ozuna"
