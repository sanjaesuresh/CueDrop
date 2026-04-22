"""Tests for QueueManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.models import Layer, QueueEntryStatus, Source, TrackModel, TransitionPlan, TransitionType
from backend.queue_manager import QueueManager


def _track(name: str = "Test") -> TrackModel:
    return TrackModel(title=name, artist="Artist")


# ---------------------------------------------------------------------------
# Basic state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initial_state_empty():
    qm = QueueManager()
    state = qm.get_state()
    assert state.current is None
    assert state.entries == []
    assert state.wildcards == []


@pytest.mark.asyncio
async def test_queue_length():
    qm = QueueManager()
    assert qm.queue_length() == 0
    await qm.lock_next(_track("A"))
    assert qm.queue_length() == 1


# ---------------------------------------------------------------------------
# lock_next
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lock_next_adds_at_position_zero():
    qm = QueueManager()
    entry = await qm.lock_next(_track("A"))
    assert entry.position == 0
    assert entry.layer == Layer.LOCKED
    assert entry.source == Source.AI


@pytest.mark.asyncio
async def test_lock_next_shifts_existing():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.lock_next(_track("B"))
    entries = qm.get_state().entries
    assert entries[0].track.title == "B"
    assert entries[0].position == 0
    assert entries[1].track.title == "A"
    assert entries[1].position == 1


@pytest.mark.asyncio
async def test_lock_next_with_transition_plan():
    qm = QueueManager()
    tp = TransitionPlan(transition_type=TransitionType.CUT)
    entry = await qm.lock_next(_track(), transition_plan=tp)
    assert entry.transition_plan is not None
    assert entry.transition_plan.transition_type == TransitionType.CUT


# ---------------------------------------------------------------------------
# add_anchor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_add_anchor():
    qm = QueueManager()
    entry = await qm.add_anchor(_track("Anchor"), source=Source.ADMIN)
    assert entry.layer == Layer.ANCHOR
    assert entry.source == Source.ADMIN


@pytest.mark.asyncio
async def test_add_anchor_appends():
    qm = QueueManager()
    await qm.lock_next(_track("First"))
    await qm.add_anchor(_track("Anchor"))
    entries = qm.get_state().entries
    assert len(entries) == 2
    assert entries[1].layer == Layer.ANCHOR


# ---------------------------------------------------------------------------
# park_wildcard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_park_wildcard():
    qm = QueueManager()
    entry = await qm.park_wildcard(_track("Wild"))
    assert entry.layer == Layer.WILDCARD
    assert entry.source == Source.GUEST
    assert len(qm.get_state().wildcards) == 1
    assert qm.queue_length() == 0  # wildcards not in main queue


# ---------------------------------------------------------------------------
# advance
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_advance_promotes_next():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.add_anchor(_track("B"))

    current = await qm.advance()
    assert current is not None
    assert current.track.title == "A"
    assert current.status == QueueEntryStatus.PLAYING
    assert qm.get_state().current.track.title == "A"
    assert qm.queue_length() == 1


@pytest.mark.asyncio
async def test_advance_marks_previous_as_played():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.add_anchor(_track("B"))

    first = await qm.advance()
    second = await qm.advance()

    assert first.status == QueueEntryStatus.PLAYED
    assert second.track.title == "B"
    assert second.status == QueueEntryStatus.PLAYING


@pytest.mark.asyncio
async def test_advance_empty_queue():
    qm = QueueManager()
    result = await qm.advance()
    assert result is None
    assert qm.get_state().current is None


@pytest.mark.asyncio
async def test_advance_reindexes():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.add_anchor(_track("B"))
    await qm.add_anchor(_track("C"))

    await qm.advance()  # A becomes current
    entries = qm.get_state().entries
    assert entries[0].position == 0
    assert entries[1].position == 1


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remove_by_position():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.add_anchor(_track("B"))
    await qm.add_anchor(_track("C"))

    removed = await qm.remove(1)
    assert removed is not None
    assert removed.track.title == "B"
    assert qm.queue_length() == 2


@pytest.mark.asyncio
async def test_remove_reindexes():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.add_anchor(_track("B"))
    await qm.add_anchor(_track("C"))

    await qm.remove(0)
    entries = qm.get_state().entries
    assert entries[0].position == 0
    assert entries[1].position == 1


@pytest.mark.asyncio
async def test_remove_nonexistent():
    qm = QueueManager()
    result = await qm.remove(99)
    assert result is None


# ---------------------------------------------------------------------------
# replan (stub)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_replan_orders_by_priority():
    qm = QueueManager()
    await qm.add_anchor(_track("Anchor"))
    await qm.lock_next(_track("Locked"))
    # After lock_next, Locked is at 0, Anchor shifted to 1

    state = await qm.replan()
    # Replan should put locked first, then anchors
    assert state.entries[0].layer == Layer.LOCKED
    assert state.entries[1].layer == Layer.ANCHOR


# ---------------------------------------------------------------------------
# Broadcast callback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_change_called():
    callback = AsyncMock()
    qm = QueueManager(on_change=callback)
    await qm.lock_next(_track())
    callback.assert_called_once()
    payload = callback.call_args[0][0]
    assert "entries" in payload
    assert "current" in payload


@pytest.mark.asyncio
async def test_no_callback_no_error():
    qm = QueueManager()
    await qm.lock_next(_track())  # should not raise


# ---------------------------------------------------------------------------
# QueueState serialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_queue_state_to_dict():
    qm = QueueManager()
    await qm.lock_next(_track("A"))
    await qm.advance()
    d = qm.get_state().to_dict()
    assert d["current"] is not None
    assert d["current"]["track"]["title"] == "A"
    assert isinstance(d["entries"], list)
    assert isinstance(d["wildcards"], list)
