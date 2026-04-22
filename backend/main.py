"""CueDrop FastAPI application — all endpoints, WebSocket managers, lifespan."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.config import load_settings
from backend.models import Source, TrackModel
from backend.queue_manager import QueueManager
from backend.vdj_client import MockVDJClient, VDJClient, VDJClientProtocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state (initialized in lifespan)
# ---------------------------------------------------------------------------

settings = load_settings()
queue_manager: QueueManager | None = None
vdj: VDJClientProtocol | None = None


# ---------------------------------------------------------------------------
# WebSocket connection managers
# ---------------------------------------------------------------------------


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.remove(ws)

    async def broadcast(self, data: dict) -> None:
        payload = json.dumps(data)
        for ws in list(self._connections):
            try:
                await ws.send_text(payload)
            except Exception:
                self._connections.remove(ws)

    @property
    def active_count(self) -> int:
        return len(self._connections)


admin_ws = ConnectionManager()
guest_ws = ConnectionManager()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


async def _broadcast_queue(data: dict) -> None:
    await admin_ws.broadcast({"type": "queue_update", "data": data})


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    global queue_manager, vdj

    queue_manager = QueueManager(on_change=_broadcast_queue)

    # Use real VDJ client if auth token is set, otherwise mock
    if settings.vdj_auth_token:
        vdj = VDJClient(host=settings.vdj_host, auth_token=settings.vdj_auth_token)
    else:
        vdj = MockVDJClient()
        logger.info("Using MockVDJClient (no VDJ_AUTH_TOKEN set)")

    logger.info("CueDrop started — VDJ: %s", type(vdj).__name__)

    yield

    if vdj:
        await vdj.close()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="CueDrop", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Queue endpoints
# ---------------------------------------------------------------------------


@app.get("/queue")
async def get_queue():
    return queue_manager.get_state().to_dict()


@app.post("/request/admin")
async def admin_request(track: TrackModel):
    entry = await queue_manager.add_anchor(track, source=Source.ADMIN)
    return entry.model_dump(mode="json")


@app.post("/skip")
async def skip():
    next_entry = await queue_manager.advance()
    if next_entry:
        return {"status": "skipped", "now_playing": next_entry.model_dump(mode="json")}
    return {"status": "queue_empty"}


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


@app.get("/status")
async def get_status():
    statuses = await vdj.get_status()
    return {"decks": [{"deck": s.deck, "artist": s.artist, "title": s.title,
                        "time_ms": s.time_ms, "bpm": s.bpm, "is_playing": s.is_playing}
                       for s in statuses]}


# ---------------------------------------------------------------------------
# WebSocket — Admin
# ---------------------------------------------------------------------------


@app.websocket("/ws/admin")
async def ws_admin(websocket: WebSocket):
    await admin_ws.connect(websocket)
    try:
        # Send current state on connect
        await websocket.send_text(json.dumps({
            "type": "queue_update",
            "data": queue_manager.get_state().to_dict(),
        }))
        while True:
            data = await websocket.receive_text()
            # Future: handle admin commands via WebSocket
            logger.debug("Admin WS message: %s", data)
    except WebSocketDisconnect:
        admin_ws.disconnect(websocket)


# ---------------------------------------------------------------------------
# WebSocket — Guest
# ---------------------------------------------------------------------------


@app.websocket("/ws/guest/{session_id}")
async def ws_guest(websocket: WebSocket, session_id: str):
    await guest_ws.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Guest WS message (session=%s): %s", session_id, data)
    except WebSocketDisconnect:
        guest_ws.disconnect(websocket)
