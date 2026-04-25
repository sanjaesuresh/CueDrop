"""Tests for DJOrchestrator — integration wiring."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from backend.models import SetState, Source, TrackModel
from backend.orchestrator import DJOrchestrator
from backend.queue_manager import QueueManager
from backend.transition_logger import QualitySignal, TransitionLogger
from backend.vdj_client import MockVDJClient


def _track(title="Test", artist="Artist", bpm=126.0) -> TrackModel:
    return TrackModel(title=title, artist=artist, bpm=bpm)


# ---------------------------------------------------------------------------
# tick
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tick_empty_no_graph():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.tick(SetState())
    assert result["queue_length"] == 0
    assert result["actions"] == []


@pytest.mark.asyncio
async def test_tick_starts_playback():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    await qm.add_anchor(_track("A"), source=Source.ADMIN)

    result = await orch.tick(SetState())
    assert "started playback" in result["actions"]
    assert qm.get_state().current is not None
    assert qm.get_state().current.track.title == "A"


# ---------------------------------------------------------------------------
# execute_transition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_transition_advances_queue():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    await qm.add_anchor(_track("A"), source=Source.ADMIN)
    await qm.add_anchor(_track("B"), source=Source.ADMIN)

    # First advance — A becomes current
    ok = await orch.execute_transition(SetState())
    assert ok
    assert qm.get_state().current.track.title == "A"

    # Second advance — B becomes current
    ok = await orch.execute_transition(SetState())
    assert ok
    assert qm.get_state().current.track.title == "B"


@pytest.mark.asyncio
async def test_execute_transition_logs():
    qm = QueueManager()
    vdj = MockVDJClient()
    tl = TransitionLogger()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj, transition_logger=tl)

    await qm.add_anchor(_track("A"), source=Source.ADMIN)
    await qm.add_anchor(_track("B"), source=Source.ADMIN)

    await orch.execute_transition(SetState())  # A becomes current
    await orch.execute_transition(SetState())  # B becomes current, transition A→B logged

    assert tl.total_transitions == 1
    logs = tl.get_logs()
    assert logs[0].to_track_id == "Artist::B"
    assert QualitySignal.COMPLETION in logs[0].signals


@pytest.mark.asyncio
async def test_execute_transition_empty_queue():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    ok = await orch.execute_transition(SetState())
    assert not ok


@pytest.mark.asyncio
async def test_execute_transition_runs_vdj_commands():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    from backend.models import TransitionPlan, TransitionType
    from backend.transition_planner import VDJCommand

    plan = TransitionPlan(
        transition_type=TransitionType.BLEND,
        commands=[
            VDJCommand(script="crossfader 50%", offset_ms=0),
            VDJCommand(script="crossfader 100%", offset_ms=1000),
        ],
    )
    await qm.lock_next(_track("A"), transition_plan=plan)

    await orch.execute_transition(SetState())
    assert len(vdj.commands) == 2
    assert "crossfader 50%" in vdj.commands[0]


# ---------------------------------------------------------------------------
# handle_skip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_skip():
    qm = QueueManager()
    vdj = MockVDJClient()
    tl = TransitionLogger()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj, transition_logger=tl)

    await qm.add_anchor(_track("A"), source=Source.ADMIN)
    await qm.add_anchor(_track("B"), source=Source.ADMIN)
    await qm.advance()  # A is now current

    # Log a transition so skip signal has something to attach to
    tl.log_transition("x", "y", "blend")

    result = await orch.handle_skip(SetState())
    assert result["status"] == "skipped"
    assert result["now_playing"] == "B"

    # Skip signal should be on latest log
    assert QualitySignal.SKIP in tl.get_logs()[-1].signals


@pytest.mark.asyncio
async def test_handle_skip_empty():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.handle_skip(SetState())
    assert result["status"] == "queue_empty"


# ---------------------------------------------------------------------------
# handle_chat_intent
# ---------------------------------------------------------------------------


@dataclass
class FakeIntent:
    type: str
    data: dict
    response: str = ""


@pytest.mark.asyncio
async def test_chat_intent_skip():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    await qm.add_anchor(_track("A"), source=Source.ADMIN)
    await qm.advance()

    result = await orch.handle_chat_intent(
        FakeIntent(type="skip", data={}), SetState()
    )
    assert result["status"] in ("skipped", "queue_empty")


@pytest.mark.asyncio
async def test_chat_intent_track_request():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.handle_chat_intent(
        FakeIntent(type="track_request", data={"title": "Cola", "artist": "CamelPhat"}),
        SetState(),
    )
    assert result["status"] == "added"
    assert result["track"] == "Cola"
    assert qm.queue_length() == 1


@pytest.mark.asyncio
async def test_chat_intent_track_request_no_title():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.handle_chat_intent(
        FakeIntent(type="track_request", data={}), SetState()
    )
    assert result["status"] == "no_track_found"


@pytest.mark.asyncio
async def test_chat_intent_energy_shift():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.handle_chat_intent(
        FakeIntent(type="energy_shift", data={"direction": "up"}), SetState()
    )
    assert result["status"] == "energy_adjusted"
    assert result["direction"] == "up"


@pytest.mark.asyncio
async def test_chat_intent_query():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    await qm.add_anchor(_track("Playing"), source=Source.ADMIN)
    await qm.advance()

    result = await orch.handle_chat_intent(
        FakeIntent(type="query", data={}), SetState()
    )
    assert result["status"] == "info"
    assert result["current"] == "Playing"


@pytest.mark.asyncio
async def test_chat_intent_unhandled():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    result = await orch.handle_chat_intent(
        FakeIntent(type="unknown_intent", data={}), SetState()
    )
    assert result["status"] == "unhandled"


# ---------------------------------------------------------------------------
# fill_queue without graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fill_queue_no_graph():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)

    added = await orch.fill_queue(SetState())
    assert added == 0


@pytest.mark.asyncio
async def test_fill_queue_no_current_track():
    qm = QueueManager()
    vdj = MockVDJClient()
    mock_graph = AsyncMock()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj, graph_client=mock_graph)

    added = await orch.fill_queue(SetState())
    assert added == 0


# ---------------------------------------------------------------------------
# transition_logger property
# ---------------------------------------------------------------------------


def test_transition_logger_property():
    qm = QueueManager()
    vdj = MockVDJClient()
    tl = TransitionLogger()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj, transition_logger=tl)
    assert orch.transition_logger is tl


def test_default_transition_logger():
    qm = QueueManager()
    vdj = MockVDJClient()
    orch = DJOrchestrator(queue_manager=qm, vdj_client=vdj)
    assert orch.transition_logger is not None
