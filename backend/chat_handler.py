"""Claude API NLU + response generation."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from anthropic import AsyncAnthropic

from backend.models import SetState

logger = logging.getLogger(__name__)

INTENT_TYPES = ("track_request", "vibe_request", "artist_request", "skip", "query", "energy_shift")

SYSTEM_PROMPT = """You are the AI behind CueDrop, an autonomous DJ system. You interpret messages from the admin DJ and extract intents.

Respond with JSON only, no markdown fences:
{
  "intent": "<one of: track_request, vibe_request, artist_request, skip, query, energy_shift>",
  "response": "<conversational response to the admin>",
  "data": {<intent-specific data>}
}

Intent-specific data:
- track_request: {"artist": "...", "title": "...", "when": "now|next|in N mins"}
- vibe_request: {"vibe": "darker|harder|deeper|chill|uplifting|..."}
- artist_request: {"artist": "..."}
- skip: {}
- query: {"about": "queue|now_playing|stats|..."}
- energy_shift: {"direction": "up|down", "amount": "slight|moderate|big"}

Current set context will be provided. Use it to make relevant responses."""


@dataclass
class Intent:
    type: str
    data: dict
    response: str


class ChatHandler:
    """Process admin chat messages via Claude API."""

    def __init__(self, api_key: str = "", model: str = "claude-sonnet-4-20250514") -> None:
        self._client = AsyncAnthropic(api_key=api_key) if api_key else None
        self._model = model

    async def process_message(self, text: str, set_state: SetState | None = None) -> Intent:
        """Send message to Claude, extract intent and response."""
        if not self._client:
            return self._fallback_parse(text)

        context = ""
        if set_state:
            context = (
                f"\nCurrent set state: phase={set_state.phase.value}, "
                f"BPM={set_state.current_bpm}, key={set_state.current_key}, "
                f"energy_target={set_state.energy_target:.1f}, "
                f"elapsed={set_state.elapsed_mins:.0f}/{set_state.set_length_mins:.0f} mins, "
                f"genres={set_state.genres}"
            )

        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": f"{text}{context}"}],
            )

            raw = response.content[0].text.strip()
            parsed = json.loads(raw)

            return Intent(
                type=parsed.get("intent", "query"),
                data=parsed.get("data", {}),
                response=parsed.get("response", ""),
            )
        except Exception as exc:
            logger.warning("Claude API error, falling back to keyword parse: %s", exc)
            return self._fallback_parse(text)

    def _fallback_parse(self, text: str) -> Intent:
        """Simple keyword-based intent extraction when API is unavailable."""
        lower = text.lower().strip()

        if lower in ("skip", "next", "skip it", "next track"):
            return Intent(type="skip", data={}, response="Skipping to next track.")

        if any(w in lower for w in ("play ", "drop ", "queue ", "put on ")):
            return Intent(
                type="track_request",
                data={"raw_query": text},
                response=f"I'll try to find and queue that for you.",
            )

        if any(w in lower for w in ("more energy", "go harder", "turn up", "pump it")):
            return Intent(
                type="energy_shift",
                data={"direction": "up", "amount": "moderate"},
                response="Bringing the energy up!",
            )

        if any(w in lower for w in ("chill", "calm down", "bring it down", "ease up")):
            return Intent(
                type="energy_shift",
                data={"direction": "down", "amount": "moderate"},
                response="Easing things down.",
            )

        if any(w in lower for w in ("darker", "deeper", "melodic", "groovy", "uplifting")):
            for vibe in ("darker", "deeper", "melodic", "groovy", "uplifting"):
                if vibe in lower:
                    return Intent(
                        type="vibe_request",
                        data={"vibe": vibe},
                        response=f"Shifting the vibe to {vibe}.",
                    )

        if any(w in lower for w in ("what", "how many", "queue", "playing", "stats")):
            return Intent(
                type="query",
                data={"about": "general"},
                response="Let me check that for you.",
            )

        return Intent(
            type="query",
            data={"raw": text},
            response="I'm not sure what you mean. Try asking about the queue, or request a track.",
        )
