"""Pydantic models for CueDrop knowledge base."""

from __future__ import annotations

import re
import uuid

from pydantic import BaseModel, field_validator, model_validator


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
    has_dj_edit: bool | None = None
    dj_edit_bpm: float | None = None

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
