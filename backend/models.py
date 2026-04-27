"""Pydantic models for CueDrop."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Layer(str, Enum):
    LOCKED = "locked"
    SOFT = "soft"
    ANCHOR = "anchor"
    WILDCARD = "wildcard"
    HORIZON = "horizon"


class Source(str, Enum):
    ADMIN = "admin"
    GUEST = "guest"
    AI = "ai"


class Phase(str, Enum):
    WARMUP = "warmup"
    BUILD = "build"
    PEAK = "peak"
    COMEDOWN = "comedown"


class TransitionType(str, Enum):
    BLEND = "blend"
    BASS_SWAP = "bass_swap"
    CUT = "cut"
    ECHO_OUT = "echo_out"
    FILTER_SWEEP = "filter_sweep"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    SLOTTED = "slotted"
    WILDCARD = "wildcard"
    EXPIRED = "expired"


class QueueEntryStatus(str, Enum):
    QUEUED = "queued"
    PLAYING = "playing"
    PLAYED = "played"
    SKIPPED = "skipped"


def generate_track_id(artist: str, title: str, remix: str | None) -> str:
    """Generate normalized track ID: artist::title::remix."""
    parts = [artist, title, remix or "original"]
    normalized = []
    for part in parts:
        segment = part.lower()
        segment = re.sub(r"[^a-z0-9\s]", " ", segment)
        segment = re.sub(r"\s+", " ", segment).strip()
        normalized.append(segment)
    return "::".join(normalized)


class TrackModel(BaseModel):
    track_id: str | None = None
    title: str
    artist: str
    remix: str | None = None
    bpm: float | None = None
    key: str | None = None
    energy: float | None = None
    genre: list[str] = []
    intro_bars: int | None = None
    outro_bars: int | None = None
    duration_ms: int | None = None
    label: str | None = None
    has_vocals_at: list[list[int]] = []  # [[start_ms, end_ms], ...] vocal time ranges
    has_dj_edit: bool | None = None
    dj_edit_bpm: float | None = None
    danceability: float = 0.0

    @model_validator(mode="after")
    def set_track_id(self) -> TrackModel:
        if self.track_id is None:
            self.track_id = generate_track_id(self.artist, self.title, self.remix)
        return self


class DJModel(BaseModel):
    name: str
    genres: list[str] = []
    profile_url: str | None = None
    set_count: int = 0


class SetModel(BaseModel):
    set_id: str | None = None
    dj_name: str
    event: str | None = None
    date: str | None = None
    venue: str | None = None
    source_url: str | None = None
    track_count: int | None = None

    @model_validator(mode="after")
    def set_defaults(self) -> SetModel:
        if self.set_id is None:
            self.set_id = uuid.uuid4().hex[:12]
        return self


class SetImport(BaseModel):
    dj: DJModel | str
    event: str | None = None
    date: str | None = None
    venue: str | None = None
    source_url: str | None = None
    tracks: list[TrackModel]

    @field_validator("dj", mode="before")
    @classmethod
    def coerce_dj(cls, v: object) -> object:
        if isinstance(v, str):
            return DJModel(name=v)
        return v


# ---------------------------------------------------------------------------
# Queue & Session models
# ---------------------------------------------------------------------------


class TransitionPlan(BaseModel):
    transition_type: TransitionType = TransitionType.BLEND
    start_bar: int | None = None
    duration_bars: int = 16


class QueueEntry(BaseModel):
    track: TrackModel
    position: int
    layer: Layer = Layer.SOFT
    source: Source = Source.AI
    status: QueueEntryStatus = QueueEntryStatus.QUEUED
    transition_plan: TransitionPlan | None = None


class GuestRequest(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    track: TrackModel
    session_id: str
    device_id: str
    status: RequestStatus = RequestStatus.PENDING
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    eta: datetime | None = None
    decline_reason: str | None = None


class SetState(BaseModel):
    phase: Phase = Phase.WARMUP
    current_bpm: float | None = None
    current_key: str | None = None
    genres: list[str] = []
    energy_target: float = 0.5
    elapsed_mins: float = 0.0
    set_length_mins: float = 120.0


class SessionSettings(BaseModel):
    genre_filter: list[str] = []
    guest_requests_enabled: bool = True
    request_window_mins: int = 30
    max_queue_depth: int = 20
    cooldown_mins: int = 15
    content_filter_clean: bool = False
    manual_approval: bool = True
    auto_action_mins: int = 5
    set_length_mins: float = 120.0
    energy_arc: str = "club_night"
    transition_aggression: float = 0.5
    genre_drift: float = 0.3


class Session(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "CueDrop Session"
    genres: list[str] = []
    settings: SessionSettings = Field(default_factory=SessionSettings)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    qr_url: str | None = None
    admin_token: str = Field(default_factory=lambda: uuid.uuid4().hex)
