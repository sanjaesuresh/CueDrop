"""Tests for QueueManager."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from backend.models import Layer, QueueEntryStatus, Source, TrackModel, TransitionPlan, TransitionType
from backend.queue_manager import QueueManager


def _track(name: str = "Test", bpm: float | None = None) -> TrackModel:
    return TrackModel(title=name, artist="Artist", bpm=bpm)


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

    state = await qm.replan()
    assert state.entries[0].layer == Layer.LOCKED
    assert state.entries[1].layer == Layer.ANCHOR


@pytest.mark.asyncio
async def test_replan_admin_before_guest_anchors():
    qm = QueueManager()
    await qm.add_anchor(_track("Guest"), source=Source.GUEST)
    await qm.add_anchor(_track("Admin"), source=Source.ADMIN)

    state = await qm.replan()
    assert state.entries[0].track.title == "Admin"
    assert state.entries[1].track.title == "Guest"


@pytest.mark.asyncio
async def test_replan_promotes_wildcard_matching_bpm():
    qm = QueueManager()
    await qm.add_anchor(_track("Anchor", bpm=126.0), source=Source.ADMIN)
    await qm.park_wildcard(_track("Wild", bpm=128.0))  # within ±5

    state = await qm.replan()
    # Wildcard should be promoted to anchor and appear in entries
    titles = [e.track.title for e in state.entries]
    assert "Wild" in titles
    assert len(state.wildcards) == 0


@pytest.mark.asyncio
async def test_replan_keeps_wildcard_when_bpm_too_far():
    qm = QueueManager()
    await qm.add_anchor(_track("Anchor", bpm=126.0), source=Source.ADMIN)
    await qm.park_wildcard(_track("Wild", bpm=140.0))  # too far

    state = await qm.replan()
    titles = [e.track.title for e in state.entries]
    assert "Wild" not in titles
    assert len(state.wildcards) == 1


@pytest.mark.asyncio
async def test_replan_wildcard_uses_current_bpm_when_no_anchors():
    qm = QueueManager()
    await qm.lock_next(_track("Playing", bpm=125.0))
    await qm.advance()  # now "Playing" is current
    await qm.park_wildcard(_track("Wild", bpm=127.0))  # within ±5

    state = await qm.replan()
    titles = [e.track.title for e in state.entries]
    assert "Wild" in titles


@pytest.mark.asyncio
async def test_replan_no_promotion_without_bpm_reference():
    qm = QueueManager()
    await qm.park_wildcard(_track("Wild", bpm=128.0))

    state = await qm.replan()
    assert len(state.wildcards) == 1
    assert len(state.entries) == 0


@pytest.mark.asyncio
async def test_replan_max_queue_depth():
    qm = QueueManager()
    for i in range(25):
        await qm.add_anchor(_track(f"T{i}"), source=Source.ADMIN)

    state = await qm.replan(max_queue_depth=10)
    assert len(state.entries) == 10


@pytest.mark.asyncio
async def test_replan_preserves_soft_after_anchors():
    qm = QueueManager()
    await qm.add_anchor(_track("Anchor"), source=Source.ADMIN)
    # Manually add a soft entry
    from backend.models import QueueEntry
    soft_entry = QueueEntry(
        track=_track("Soft"),
        position=1,
        layer=Layer.SOFT,
        source=Source.AI,
    )
    qm._state.entries.append(soft_entry)

    state = await qm.replan()
    layers = [e.layer for e in state.entries]
    anchor_idx = layers.index(Layer.ANCHOR)
    soft_idx = layers.index(Layer.SOFT)
    assert anchor_idx < soft_idx


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
