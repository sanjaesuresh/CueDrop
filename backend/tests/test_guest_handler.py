"""Tests for GuestHandler."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from backend.guest_handler import GuestHandler
from backend.models import RequestStatus, SessionSettings, SetState, TrackModel


def _track(title: str = "Cola", artist: str = "CamelPhat") -> TrackModel:
    return TrackModel(title=title, artist=artist, bpm=125.0, genre=["tech house"])


# ---------------------------------------------------------------------------
# submit_request — basic
# ---------------------------------------------------------------------------


def test_submit_request_creates_pending():
    gh = GuestHandler(settings=SessionSettings(manual_approval=True))
    req = gh.submit_request(_track(), "sess1", "dev1")
    assert req.status == RequestStatus.PENDING
    assert req.session_id == "sess1"
    assert req.device_id == "dev1"


def test_submit_request_auto_approve():
    gh = GuestHandler(settings=SessionSettings(manual_approval=False))
    req = gh.submit_request(_track(), "sess1", "dev1")
    assert req.status == RequestStatus.APPROVED


# ---------------------------------------------------------------------------
# submit_request — guest requests disabled
# ---------------------------------------------------------------------------


def test_submit_request_disabled():
    gh = GuestHandler(settings=SessionSettings(guest_requests_enabled=False))
    req = gh.submit_request(_track(), "sess1", "dev1")
    assert req.status == RequestStatus.DECLINED
    assert "disabled" in req.decline_reason.lower()


# ---------------------------------------------------------------------------
# submit_request — cooldown
# ---------------------------------------------------------------------------


def test_cooldown_blocks_second_request():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=15))
    gh.submit_request(_track("A"), "s", "dev1")
    req2 = gh.submit_request(_track("B"), "s", "dev1")
    assert req2.status == RequestStatus.DECLINED
    assert "wait" in req2.decline_reason.lower()


def test_cooldown_allows_after_expiry():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=1))
    gh.submit_request(_track("A"), "s", "dev1")
    # Manually set the history to be old enough
    gh._device_history["dev1"] = [datetime.now(UTC) - timedelta(minutes=2)]
    req2 = gh.submit_request(_track("B"), "s", "dev1")
    assert req2.status != RequestStatus.DECLINED or "wait" not in (req2.decline_reason or "").lower()


# ---------------------------------------------------------------------------
# submit_request — abuse detection
# ---------------------------------------------------------------------------


def test_abuse_detection():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=0))
    # Submit 6 requests (> 5 threshold)
    for i in range(6):
        gh._device_history.setdefault("dev1", []).append(datetime.now(UTC) - timedelta(hours=1))
    req = gh.submit_request(_track(), "s", "dev1")
    assert req.status == RequestStatus.DECLINED
    assert "too many" in req.decline_reason.lower()


# ---------------------------------------------------------------------------
# submit_request — track evaluation
# ---------------------------------------------------------------------------


def test_hard_fail_bpm_mismatch():
    gh = GuestHandler(settings=SessionSettings(manual_approval=False))
    track = TrackModel(title="T", artist="A", bpm=170.0)
    state = SetState(current_bpm=126.0)
    req = gh.submit_request(track, "s", "dev1", set_state=state)
    assert req.status == RequestStatus.DECLINED


def test_soft_fail_becomes_wildcard():
    gh = GuestHandler(settings=SessionSettings(manual_approval=False))
    track = TrackModel(title="T", artist="A", genre=["drum and bass"])
    state = SetState(genres=["tech house"])
    req = gh.submit_request(track, "s", "dev1", set_state=state)
    assert req.status == RequestStatus.WILDCARD


# ---------------------------------------------------------------------------
# approve / decline
# ---------------------------------------------------------------------------


def test_approve():
    gh = GuestHandler()
    req = gh.submit_request(_track(), "s", "dev1")
    assert req.status == RequestStatus.PENDING
    approved = gh.approve(req.id)
    assert approved.status == RequestStatus.APPROVED


def test_decline():
    gh = GuestHandler()
    req = gh.submit_request(_track(), "s", "dev1")
    declined = gh.decline(req.id, "Not tonight")
    assert declined.status == RequestStatus.DECLINED
    assert declined.decline_reason == "Not tonight"


def test_approve_nonexistent():
    gh = GuestHandler()
    assert gh.approve("nonexistent") is None


def test_decline_nonexistent():
    gh = GuestHandler()
    assert gh.decline("nonexistent") is None


# ---------------------------------------------------------------------------
# get_pending
# ---------------------------------------------------------------------------


def test_get_pending():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=0))
    gh.submit_request(_track("A"), "s", "dev1")
    gh.submit_request(_track("B"), "s", "dev2")
    pending = gh.get_pending()
    assert len(pending) == 2


def test_get_pending_excludes_approved():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=0))
    req = gh.submit_request(_track("A"), "s", "dev1")
    gh.approve(req.id)
    pending = gh.get_pending()
    assert len(pending) == 0


# ---------------------------------------------------------------------------
# auto_action_expired
# ---------------------------------------------------------------------------


def test_auto_approve_expired():
    gh = GuestHandler()
    req = gh.submit_request(_track(), "s", "dev1")
    result = gh.auto_action_expired(req.id, "approve")
    assert result.status == RequestStatus.APPROVED


def test_auto_decline_expired():
    gh = GuestHandler()
    req = gh.submit_request(_track(), "s", "dev1")
    result = gh.auto_action_expired(req.id, "decline")
    assert result.status == RequestStatus.DECLINED


def test_auto_action_nonexistent():
    gh = GuestHandler()
    assert gh.auto_action_expired("nope") is None


# ---------------------------------------------------------------------------
# check_cooldown
# ---------------------------------------------------------------------------


def test_check_cooldown_no_history():
    gh = GuestHandler()
    assert gh.check_cooldown("dev1") is False


def test_check_cooldown_recent():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=15))
    gh._device_history["dev1"] = [datetime.now(UTC)]
    assert gh.check_cooldown("dev1") is True


def test_check_cooldown_expired():
    gh = GuestHandler(settings=SessionSettings(cooldown_mins=1))
    gh._device_history["dev1"] = [datetime.now(UTC) - timedelta(minutes=5)]
    assert gh.check_cooldown("dev1") is False
