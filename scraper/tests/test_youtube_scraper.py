"""Tests for YouTube scraper — no network calls."""

from __future__ import annotations

from scraper.youtube_scraper import (
    DownloadResult,
    SetMetadata,
    parse_tracklist_from_description,
)


# ---------------------------------------------------------------------------
# Dataclass defaults
# ---------------------------------------------------------------------------


def test_download_result_defaults():
    r = DownloadResult(url="https://youtube.com/watch?v=abc")
    assert r.url == "https://youtube.com/watch?v=abc"
    assert r.success is False
    assert r.file_path == ""
    assert r.error is None


def test_set_metadata_defaults():
    m = SetMetadata()
    assert m.title == ""
    assert m.duration_s == 0.0
    assert m.view_count == 0


# ---------------------------------------------------------------------------
# parse_tracklist_from_description
# ---------------------------------------------------------------------------


def test_parse_mm_ss_format():
    desc = """DJ Set Tracklist:
00:00 Fisher - Losing It
03:45 CamelPhat - Cola
07:20 Chris Lake - Turn Off The Lights
"""
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 3
    assert tracks[0].artist == "Fisher"
    assert tracks[0].title == "Losing It"
    assert tracks[0].timestamp_s == 0.0
    assert tracks[1].artist == "CamelPhat"
    assert tracks[1].title == "Cola"
    assert tracks[1].timestamp_s == 225.0  # 3*60 + 45
    assert tracks[2].timestamp_s == 440.0  # 7*60 + 20


def test_parse_hh_mm_ss_format():
    desc = """1:00:00 Artist A - Track A
1:05:30 Artist B - Track B
"""
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 2
    assert tracks[0].timestamp_s == 3600.0
    assert tracks[1].timestamp_s == 3930.0  # 1*3600 + 5*60 + 30


def test_parse_bracket_format():
    desc = """[00:00] Fisher - Losing It
[05:30] Dom Dolla - Rhyme Dust
"""
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 2
    assert tracks[0].artist == "Fisher"
    assert tracks[1].artist == "Dom Dolla"


def test_parse_en_dash_separator():
    desc = "00:00 Fisher – Losing It\n"
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 1
    assert tracks[0].artist == "Fisher"
    assert tracks[0].title == "Losing It"


def test_parse_no_artist_separator():
    desc = "00:00 Some Track Name\n"
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 1
    assert tracks[0].artist == ""
    assert tracks[0].title == "Some Track Name"


def test_parse_strips_suffixes():
    desc = "00:00 Artist - Track (Official Audio)\n"
    tracks = parse_tracklist_from_description(desc)
    assert tracks[0].title == "Track"


def test_parse_empty_description():
    assert parse_tracklist_from_description("") == []


def test_parse_no_timestamps():
    desc = "This is just a regular description with no timestamps."
    assert parse_tracklist_from_description(desc) == []


def test_parse_mixed_content():
    desc = """Check out my set!

00:00 Fisher - Losing It
Subscribe for more!
05:30 CamelPhat - Cola

Like and comment below!
"""
    tracks = parse_tracklist_from_description(desc)
    assert len(tracks) == 2


def test_all_tracks_have_description_source():
    desc = "00:00 A - B\n01:00 C - D\n"
    tracks = parse_tracklist_from_description(desc)
    assert all(t.source == "description" for t in tracks)
