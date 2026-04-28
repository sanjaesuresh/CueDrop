"""DJ Orchestrator — ties together queue, brain, planner, VDJ, and logger (Phase 3)."""

from __future__ import annotations

import logging

from backend.models import SetState, Source, TrackModel
from backend.queue_manager import QueueManager
from backend.transition_logger import QualitySignal, TransitionLogger
from backend.vdj_client import VDJClientProtocol

logger = logging.getLogger(__name__)

# Minimum queue entries before auto-fill triggers
MIN_QUEUE_DEPTH = 3

# How often the learning cycle runs (every N ticks)
LEARNING_CYCLE_INTERVAL = 10


class DJOrchestrator:
    """Orchestrates the autonomous DJ loop: select, plan, execute, log."""

    def __init__(
        self,
        queue_manager: QueueManager,
        vdj_client: VDJClientProtocol,
        transition_logger: TransitionLogger | None = None,
        graph_client=None,
        edge_reweighter=None,
    ) -> None:
        self._queue = queue_manager
        self._vdj = vdj_client
        self._logger = transition_logger or TransitionLogger()
        self._graph = graph_client
        self._edge_reweighter = edge_reweighter
        self._tick_count: int = 0
        self._last_learning_index: int = 0

    async def tick(self, set_state: SetState) -> dict:
        """Periodic tick — fill queue if low, execute transitions if ready.

        Returns a status dict describing what actions were taken.
        """
        self._tick_count += 1
        actions: list[str] = []

        # Fill queue if running low
        if self._queue.queue_length() < MIN_QUEUE_DEPTH:
            filled = await self.fill_queue(set_state)
            if filled > 0:
                actions.append(f"filled {filled} tracks")

        # Check if we should execute the next transition
        state = self._queue.get_state()
        if state.current is None and state.entries:
            await self.execute_transition(set_state)
            actions.append("started playback")

        # Periodic learning cycle
        if self._tick_count % LEARNING_CYCLE_INTERVAL == 0:
            updated = await self.run_learning_cycle()
            if updated > 0:
                actions.append(f"learning: updated {updated} edges")

        return {"actions": actions, "queue_length": self._queue.queue_length()}

    async def fill_queue(self, set_state: SetState, count: int = 3) -> int:
        """Use DJBrain to select next tracks from graph neighbors.

        Returns number of tracks added.
        """
        if self._graph is None:
            return 0

        from backend.dj_brain import select_next

        added = 0
        state = self._queue.get_state()
        current_track = None

        if state.current:
            current_track = state.current.track
        elif state.entries:
            current_track = state.entries[-1].track

        if current_track is None:
            return 0

        for _ in range(count):
            try:
                track_id = current_track.track_id or f"{current_track.artist}::{current_track.title}"
                neighbors = await self._graph.get_neighbors(track_id)
                if not neighbors:
                    break

                result = select_next(current_track, neighbors, set_state)
                if result is None:
                    break

                next_track = TrackModel(
                    title=result.track.get("title", ""),
                    artist=result.track.get("artist", ""),
                    bpm=result.track.get("bpm"),
                    key=result.track.get("key"),
                    energy=result.track.get("energy"),
                )

                # Plan transition
                from backend.transition_planner import plan as plan_transition

                plan = plan_transition(current_track, next_track, set_state)
                await self._queue.lock_next(next_track, transition_plan=plan)

                current_track = next_track
                added += 1

            except Exception as exc:
                logger.warning("Failed to fill queue: %s", exc)
                break

        return added

    async def execute_transition(self, set_state: SetState) -> bool:
        """Execute the planned transition for the next track.

        Returns True if transition was executed.
        """
        state = self._queue.get_state()
        if not state.entries:
            return False

        next_entry = state.entries[0]
        plan = next_entry.transition_plan

        # Execute VDJ commands if we have a plan
        if plan and plan.commands:
            for cmd in plan.commands:
                try:
                    await self._vdj.execute(cmd.script)
                except Exception as exc:
                    logger.warning("VDJ command failed: %s — %s", cmd.script, exc)

        # Advance queue
        previous = state.current
        entry = await self._queue.advance()

        if entry is None:
            return False

        # Log the transition
        if previous:
            from_id = previous.track.track_id or f"{previous.track.artist}::{previous.track.title}"
            to_id = entry.track.track_id or f"{entry.track.artist}::{entry.track.title}"
            self._logger.log_transition(
                from_track_id=from_id,
                to_track_id=to_id,
                transition_type=plan.transition_type.value if plan else "cut",
                set_phase=set_state.phase.value if set_state.phase else "",
                source=entry.source.value if entry.source else "ai",
            )

            # Add completion signal for the previous track (it played to the end)
            self._logger.add_signal_to_latest(QualitySignal.COMPLETION)

            # Trigger edge reweighting if available
            await self._reweight_latest_transition()

        return True

    async def _reweight_latest_transition(self) -> bool:
        """Reweight the edge for the most recent logged transition.

        Returns True if the edge weight was updated.
        """
        if self._edge_reweighter is None or self._graph is None:
            return False

        logs = self._logger.get_recent(1)
        if not logs:
            return False

        latest = logs[0]
        if not latest.signals:
            return False

        quality = self._logger.get_edge_quality(
            latest.from_track_id, latest.to_track_id
        )

        try:
            await self._graph.update_edge_weight(
                from_id=latest.from_track_id,
                to_id=latest.to_track_id,
                self_play_quality=quality,
            )
            logger.debug(
                "Reweighted edge %s -> %s: quality=%.3f",
                latest.from_track_id,
                latest.to_track_id,
                quality,
            )
            return True
        except Exception as exc:
            logger.warning("Edge reweight failed: %s", exc)
            return False

    async def run_learning_cycle(self) -> int:
        """Process recent transition logs and update edge weights.

        Processes all logs since the last learning cycle.
        Returns the count of edges updated.
        """
        if self._edge_reweighter is None or self._graph is None:
            return 0

        all_logs = self._logger.get_logs()
        pending = all_logs[self._last_learning_index:]
        self._last_learning_index = len(all_logs)

        updated = 0
        for log in pending:
            if not log.signals:
                continue

            quality = self._logger.get_edge_quality(
                log.from_track_id, log.to_track_id
            )

            try:
                await self._graph.update_edge_weight(
                    from_id=log.from_track_id,
                    to_id=log.to_track_id,
                    self_play_quality=quality,
                )
                updated += 1
            except Exception as exc:
                logger.warning(
                    "Learning cycle reweight failed for %s -> %s: %s",
                    log.from_track_id,
                    log.to_track_id,
                    exc,
                )

        if updated:
            logger.info("Learning cycle: updated %d edge weights", updated)

        return updated

    async def handle_skip(self, set_state: SetState) -> dict:
        """Handle a skip request — advance queue and log skip signal."""
        # Log skip signal for current transition
        self._logger.add_signal_to_latest(QualitySignal.SKIP)

        entry = await self._queue.advance()
        if entry:
            return {"status": "skipped", "now_playing": entry.track.title}
        return {"status": "queue_empty"}

    async def handle_chat_intent(self, intent_result, set_state: SetState) -> dict:
        """Route chat intents to appropriate actions.

        Args:
            intent_result: Result from ChatHandler with .type, .data, .response
            set_state: Current set state.

        Returns:
            dict with action taken and any additional data.
        """
        intent_type = intent_result.type

        if intent_type == "skip":
            return await self.handle_skip(set_state)

        if intent_type == "track_request":
            title = intent_result.data.get("title", "")
            artist = intent_result.data.get("artist", "")

            if title:
                track = TrackModel(title=title, artist=artist)
                entry = await self._queue.add_anchor(track, source=Source.ADMIN)
                await self._queue.replan()
                return {
                    "status": "added",
                    "track": title,
                    "position": entry.position,
                }

            return {"status": "no_track_found"}

        if intent_type == "energy_shift":
            direction = intent_result.data.get("direction", "up")
            return {"status": "energy_adjusted", "direction": direction}

        if intent_type in ("vibe_request", "artist_request"):
            query = intent_result.data.get("query", "") or intent_result.data.get("artist", "")
            return {"status": "searching", "query": query}

        if intent_type == "query":
            state = self._queue.get_state()
            return {
                "status": "info",
                "queue_length": len(state.entries),
                "current": state.current.track.title if state.current else None,
            }

        return {"status": "unhandled", "intent": intent_type}

    @property
    def transition_logger(self) -> TransitionLogger:
        return self._logger
