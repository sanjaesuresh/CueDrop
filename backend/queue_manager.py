"""Queue layers: locked / soft / anchor / wildcard / horizon."""

from __future__ import annotations

import logging
from typing import Callable, Coroutine

from backend.models import (
    Layer,
    QueueEntry,
    QueueEntryStatus,
    Source,
    TrackModel,
    TransitionPlan,
)

logger = logging.getLogger(__name__)

# Type alias for WebSocket broadcast callback
BroadcastFn = Callable[[dict], Coroutine]


class QueueState:
    """Snapshot of the 5-layer queue."""

    def __init__(self) -> None:
        self.current: QueueEntry | None = None
        self.entries: list[QueueEntry] = []
        self.wildcards: list[QueueEntry] = []

    def to_dict(self) -> dict:
        return {
            "current": self.current.model_dump(mode="json") if self.current else None,
            "entries": [e.model_dump(mode="json") for e in self.entries],
            "wildcards": [w.model_dump(mode="json") for w in self.wildcards],
        }


class QueueManager:
    """5-layer queue state management."""

    def __init__(self, on_change: BroadcastFn | None = None) -> None:
        self._state = QueueState()
        self._on_change = on_change

    async def _notify(self) -> None:
        if self._on_change:
            await self._on_change(self._state.to_dict())

    def get_state(self) -> QueueState:
        return self._state

    async def lock_next(self, track: TrackModel, transition_plan: TransitionPlan | None = None) -> QueueEntry:
        """Add a track as the next locked entry (position 0 = next up)."""
        entry = QueueEntry(
            track=track,
            position=0,
            layer=Layer.LOCKED,
            source=Source.AI,
            transition_plan=transition_plan,
        )
        # Shift existing entries
        for e in self._state.entries:
            e.position += 1
        self._state.entries.insert(0, entry)
        await self._notify()
        return entry

    async def add_anchor(
        self,
        track: TrackModel,
        source: Source = Source.ADMIN,
        window_mins: int = 30,
        priority: int = 0,
    ) -> QueueEntry:
        """Add an anchor track — will be woven into the queue during replan."""
        position = len(self._state.entries)
        entry = QueueEntry(
            track=track,
            position=position,
            layer=Layer.ANCHOR,
            source=source,
        )
        self._state.entries.append(entry)
        await self._notify()
        return entry

    async def park_wildcard(self, track: TrackModel, request_id: str | None = None) -> QueueEntry:
        """Park a guest request as a wildcard — may be promoted during replan."""
        entry = QueueEntry(
            track=track,
            position=-1,
            layer=Layer.WILDCARD,
            source=Source.GUEST,
        )
        self._state.wildcards.append(entry)
        await self._notify()
        return entry

    async def advance(self) -> QueueEntry | None:
        """Current track finishes — promote next entry to current."""
        if self._state.current:
            self._state.current.status = QueueEntryStatus.PLAYED

        if not self._state.entries:
            self._state.current = None
            await self._notify()
            return None

        next_entry = self._state.entries.pop(0)
        next_entry.status = QueueEntryStatus.PLAYING
        self._state.current = next_entry

        # Re-index positions
        for i, e in enumerate(self._state.entries):
            e.position = i

        await self._notify()
        return next_entry

    async def remove(self, position: int) -> QueueEntry | None:
        """Remove an entry by position."""
        for i, e in enumerate(self._state.entries):
            if e.position == position:
                removed = self._state.entries.pop(i)
                # Re-index
                for j, entry in enumerate(self._state.entries):
                    entry.position = j
                await self._notify()
                return removed
        return None

    async def replan(self) -> QueueState:
        """Stub replan — preserves locked and anchor entries, fills gaps with soft entries.

        Full implementation in Phase 2 (Stream D) will use graph + DJBrain.
        """
        # Sort: locked first, then anchors, then soft
        locked = [e for e in self._state.entries if e.layer == Layer.LOCKED]
        anchors = [e for e in self._state.entries if e.layer == Layer.ANCHOR]
        soft = [e for e in self._state.entries if e.layer == Layer.SOFT]
        horizon = [e for e in self._state.entries if e.layer == Layer.HORIZON]

        reordered = locked + anchors + soft + horizon
        for i, e in enumerate(reordered):
            e.position = i
        self._state.entries = reordered

        await self._notify()
        return self._state

    def queue_length(self) -> int:
        return len(self._state.entries)
