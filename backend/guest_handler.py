"""Guest request validation, approval flow, cooldowns."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from backend.dj_brain import evaluate_request
from backend.models import (
    GuestRequest,
    RequestStatus,
    SessionSettings,
    SetState,
    TrackModel,
)

logger = logging.getLogger(__name__)


class GuestHandler:
    """Manage guest song requests — validation, cooldowns, approval."""

    def __init__(self, settings: SessionSettings | None = None) -> None:
        self._settings = settings or SessionSettings()
        self._requests: dict[str, GuestRequest] = {}
        self._device_history: dict[str, list[datetime]] = {}

    def check_cooldown(self, device_id: str) -> bool:
        """Return True if device is in cooldown (should NOT submit)."""
        history = self._device_history.get(device_id, [])
        if not history:
            return False
        last = max(history)
        cooldown = timedelta(minutes=self._settings.cooldown_mins)
        return datetime.now(UTC) - last < cooldown

    def _check_abuse(self, device_id: str) -> bool:
        """Return True if device has sent too many requests (>5 in session)."""
        return len(self._device_history.get(device_id, [])) > 5

    def submit_request(
        self,
        track: TrackModel,
        session_id: str,
        device_id: str,
        set_state: SetState | None = None,
    ) -> GuestRequest:
        """Validate and create a guest request."""
        if not self._settings.guest_requests_enabled:
            req = GuestRequest(
                track=track, session_id=session_id, device_id=device_id,
                status=RequestStatus.DECLINED,
                decline_reason="Guest requests are currently disabled.",
            )
            self._requests[req.id] = req
            return req

        if self.check_cooldown(device_id):
            req = GuestRequest(
                track=track, session_id=session_id, device_id=device_id,
                status=RequestStatus.DECLINED,
                decline_reason=f"Please wait {self._settings.cooldown_mins} minutes between requests.",
            )
            self._requests[req.id] = req
            return req

        if self._check_abuse(device_id):
            req = GuestRequest(
                track=track, session_id=session_id, device_id=device_id,
                status=RequestStatus.DECLINED,
                decline_reason="Too many requests from this device.",
            )
            self._requests[req.id] = req
            return req

        # Evaluate track fit
        state = set_state or SetState()
        evaluation = evaluate_request(track, state)

        if evaluation.result == "hard_fail":
            req = GuestRequest(
                track=track, session_id=session_id, device_id=device_id,
                status=RequestStatus.DECLINED,
                decline_reason=evaluation.reason,
            )
        elif evaluation.result == "soft_fail":
            req = GuestRequest(
                track=track, session_id=session_id, device_id=device_id,
                status=RequestStatus.WILDCARD,
            )
        else:
            if self._settings.manual_approval:
                req = GuestRequest(
                    track=track, session_id=session_id, device_id=device_id,
                    status=RequestStatus.PENDING,
                )
            else:
                req = GuestRequest(
                    track=track, session_id=session_id, device_id=device_id,
                    status=RequestStatus.APPROVED,
                )

        # Record device history
        self._device_history.setdefault(device_id, []).append(datetime.now(UTC))
        self._requests[req.id] = req
        return req

    def approve(self, request_id: str) -> GuestRequest | None:
        """Approve a pending request."""
        req = self._requests.get(request_id)
        if req is None:
            return None
        if req.status != RequestStatus.PENDING:
            return req
        req.status = RequestStatus.APPROVED
        return req

    def decline(self, request_id: str, reason: str = "Declined by admin") -> GuestRequest | None:
        """Decline a pending request."""
        req = self._requests.get(request_id)
        if req is None:
            return None
        req.status = RequestStatus.DECLINED
        req.decline_reason = reason
        return req

    def get_pending(self) -> list[GuestRequest]:
        """Return all pending requests."""
        return [r for r in self._requests.values() if r.status == RequestStatus.PENDING]

    def get_request(self, request_id: str) -> GuestRequest | None:
        return self._requests.get(request_id)

    def auto_action_expired(self, request_id: str, action_type: str = "approve") -> GuestRequest | None:
        """Auto-approve or auto-decline an expired pending request."""
        req = self._requests.get(request_id)
        if req is None or req.status != RequestStatus.PENDING:
            return req
        if action_type == "approve":
            req.status = RequestStatus.APPROVED
        else:
            req.status = RequestStatus.DECLINED
            req.decline_reason = "Auto-declined (no admin response)"
        return req
