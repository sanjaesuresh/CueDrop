"""Tests for extended models — enums, QueueEntry, GuestRequest, SetState, Session."""

from __future__ import annotations

from backend.models import (
    GuestRequest,
    Layer,
    Phase,
    QueueEntry,
    QueueEntryStatus,
    RequestStatus,
    Session,
    SessionSettings,
    SetState,
    Source,
    TrackModel,
    TransitionPlan,
    TransitionType,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestEnums:
    def test_layer_values(self):
        assert Layer.LOCKED == "locked"
        assert Layer.WILDCARD == "wildcard"
        assert len(Layer) == 5

    def test_source_values(self):
        assert Source.ADMIN == "admin"
        assert Source.GUEST == "guest"
        assert Source.AI == "ai"

    def test_phase_values(self):
        assert Phase.WARMUP == "warmup"
        assert Phase.PEAK == "peak"
        assert len(Phase) == 4

    def test_transition_type_values(self):
        assert TransitionType.BLEND == "blend"
        assert TransitionType.BASS_SWAP == "bass_swap"
        assert len(TransitionType) == 5

    def test_request_status_values(self):
        assert RequestStatus.PENDING == "pending"
        assert RequestStatus.WILDCARD == "wildcard"
        assert len(RequestStatus) == 6

    def test_queue_entry_status_values(self):
        assert QueueEntryStatus.QUEUED == "queued"
        assert QueueEntryStatus.PLAYING == "playing"
        assert len(QueueEntryStatus) == 4


# ---------------------------------------------------------------------------
# TransitionPlan
# ---------------------------------------------------------------------------


class TestTransitionPlan:
    def test_defaults(self):
        tp = TransitionPlan()
        assert tp.transition_type == TransitionType.BLEND
        assert tp.start_bar is None
        assert tp.duration_bars == 16

    def test_custom(self):
        tp = TransitionPlan(transition_type=TransitionType.CUT, start_bar=4, duration_bars=1)
        assert tp.transition_type == TransitionType.CUT
        assert tp.start_bar == 4


# ---------------------------------------------------------------------------
# QueueEntry
# ---------------------------------------------------------------------------


class TestQueueEntry:
    def test_minimal(self):
        track = TrackModel(title="Test", artist="Artist")
        qe = QueueEntry(track=track, position=0)
        assert qe.layer == Layer.SOFT
        assert qe.source == Source.AI
        assert qe.status == QueueEntryStatus.QUEUED
        assert qe.transition_plan is None

    def test_with_transition_plan(self):
        track = TrackModel(title="Test", artist="Artist")
        tp = TransitionPlan(transition_type=TransitionType.BASS_SWAP)
        qe = QueueEntry(track=track, position=1, layer=Layer.ANCHOR, source=Source.ADMIN, transition_plan=tp)
        assert qe.layer == Layer.ANCHOR
        assert qe.transition_plan.transition_type == TransitionType.BASS_SWAP


# ---------------------------------------------------------------------------
# GuestRequest
# ---------------------------------------------------------------------------


class TestGuestRequest:
    def test_defaults(self):
        track = TrackModel(title="Cola", artist="CamelPhat")
        gr = GuestRequest(track=track, session_id="sess1", device_id="dev1")
        assert gr.status == RequestStatus.PENDING
        assert gr.id  # auto-generated
        assert gr.submitted_at is not None
        assert gr.eta is None
        assert gr.decline_reason is None

    def test_unique_ids(self):
        track = TrackModel(title="Cola", artist="CamelPhat")
        a = GuestRequest(track=track, session_id="s", device_id="d")
        b = GuestRequest(track=track, session_id="s", device_id="d")
        assert a.id != b.id


# ---------------------------------------------------------------------------
# SetState
# ---------------------------------------------------------------------------


class TestSetState:
    def test_defaults(self):
        ss = SetState()
        assert ss.phase == Phase.WARMUP
        assert ss.current_bpm is None
        assert ss.energy_target == 0.5
        assert ss.set_length_mins == 120.0

    def test_custom(self):
        ss = SetState(phase=Phase.PEAK, current_bpm=128.0, current_key="7A", energy_target=0.9)
        assert ss.phase == Phase.PEAK
        assert ss.current_bpm == 128.0


# ---------------------------------------------------------------------------
# SessionSettings
# ---------------------------------------------------------------------------


class TestSessionSettings:
    def test_defaults(self):
        s = SessionSettings()
        assert s.guest_requests_enabled is True
        assert s.manual_approval is True
        assert s.cooldown_mins == 15
        assert s.energy_arc == "club_night"

    def test_custom(self):
        s = SessionSettings(manual_approval=False, set_length_mins=60.0)
        assert s.manual_approval is False
        assert s.set_length_mins == 60.0


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class TestSession:
    def test_defaults(self):
        s = Session()
        assert s.name == "CueDrop Session"
        assert s.id  # auto-generated
        assert s.admin_token  # auto-generated
        assert s.qr_url is None
        assert isinstance(s.settings, SessionSettings)

    def test_unique_ids(self):
        a = Session()
        b = Session()
        assert a.id != b.id
        assert a.admin_token != b.admin_token

    def test_custom(self):
        s = Session(name="Pool Party", genres=["tech house", "house"])
        assert s.name == "Pool Party"
        assert s.genres == ["tech house", "house"]
