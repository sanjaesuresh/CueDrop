"""CueDrop FastAPI application — all endpoints, WebSocket managers, lifespan."""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.chat_handler import ChatHandler
from backend.config import load_settings
from backend.guest_handler import GuestHandler
from backend.models import Session, SetState, Source, TrackModel
from backend.music_resolver import MusicResolver
from backend.orchestrator import DJOrchestrator
from backend.qr_generator import generate as generate_qr
from backend.queue_manager import QueueManager
from backend.scraper_service import ScraperService
from backend.vdj_client import MockVDJClient, VDJClient, VDJClientProtocol

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Global state (initialized in lifespan)
# ---------------------------------------------------------------------------

settings = load_settings()
queue_manager: QueueManager | None = None
vdj: VDJClientProtocol | None = None
chat_handler: ChatHandler | None = None
guest_handler: GuestHandler | None = None
scraper_service: ScraperService | None = None
music_resolver: MusicResolver | None = None
orchestrator: DJOrchestrator | None = None
session: Session | None = None
set_state: SetState = SetState()


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
    global queue_manager, vdj, chat_handler, guest_handler, scraper_service, music_resolver, orchestrator, session

    queue_manager = QueueManager(on_change=_broadcast_queue)
    chat_handler = ChatHandler(api_key=settings.anthropic_api_key)
    guest_handler = GuestHandler()
    scraper_service = ScraperService()
    music_resolver = MusicResolver(
        local_library_path=settings.local_library_path,
        spotify_client_id=settings.spotify_client_id,
        spotify_client_secret=settings.spotify_client_secret,
    )
    session = Session()

    # Use real VDJ client if auth token is set, otherwise mock
    if settings.vdj_auth_token:
        vdj = VDJClient(host=settings.vdj_host, auth_token=settings.vdj_auth_token)
    else:
        vdj = MockVDJClient()
        logger.info("Using MockVDJClient (no VDJ_AUTH_TOKEN set)")

    orchestrator = DJOrchestrator(queue_manager=queue_manager, vdj_client=vdj)

    logger.info("CueDrop started — VDJ: %s", type(vdj).__name__)

    yield

    if music_resolver:
        await music_resolver.close()
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
    return await orchestrator.handle_skip(set_state)


@app.post("/tick")
async def tick():
    return await orchestrator.tick(set_state)


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


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    text: str


@app.post("/chat")
async def chat(msg: ChatMessage):
    result = await chat_handler.process_message(msg.text, set_state)
    action = await orchestrator.handle_chat_intent(result, set_state)
    return {"intent": result.type, "data": result.data, "response": result.response, "action": action}


# ---------------------------------------------------------------------------
# Guest requests
# ---------------------------------------------------------------------------


class GuestRequestBody(BaseModel):
    track: TrackModel
    session_id: str
    device_id: str


@app.post("/request/guest")
async def guest_request(body: GuestRequestBody):
    req = guest_handler.submit_request(body.track, body.session_id, body.device_id, set_state)
    return req.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------


@app.get("/requests/pending")
async def pending_requests():
    return [r.model_dump(mode="json") for r in guest_handler.get_pending()]


@app.post("/approve/{request_id}")
async def approve_request(request_id: str):
    req = guest_handler.approve(request_id)
    if req is None:
        return {"error": "Request not found"}
    if req.status.value == "approved":
        await queue_manager.add_anchor(req.track, source=Source.GUEST)
    return req.model_dump(mode="json")


@app.post("/decline/{request_id}")
async def decline_request(request_id: str, reason: str = "Declined by admin"):
    req = guest_handler.decline(request_id, reason)
    if req is None:
        return {"error": "Request not found"}
    return req.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Session & QR
# ---------------------------------------------------------------------------


@app.get("/session/qr")
async def session_qr():
    png = generate_qr(session.id)
    return Response(content=png, media_type="image/png")


@app.get("/session/current")
async def get_current_session():
    return {
        "id": session.id,
        "name": session.name,
        "genres": session.genres,
        "now_playing": queue_manager.get_state().current.model_dump(mode="json")
        if queue_manager.get_state().current
        else None,
    }


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    return {
        "id": session.id,
        "name": session.name,
        "genres": session.genres,
        "now_playing": queue_manager.get_state().current.model_dump(mode="json")
        if queue_manager.get_state().current
        else None,
    }


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@app.put("/settings")
async def update_settings(new_settings: dict):
    for key, value in new_settings.items():
        if hasattr(session.settings, key):
            setattr(session.settings, key, value)
    return session.settings.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Search (guest Spotify proxy)
# ---------------------------------------------------------------------------


@app.get("/search")
async def search(q: str, limit: int = 10):
    results = await music_resolver.search(q, limit=limit)
    return [
        {
            "spotify_id": r.spotify_id,
            "title": r.title,
            "artist": r.artist,
            "album": r.album,
            "duration_ms": r.duration_ms,
            "preview_url": r.preview_url,
        }
        for r in results
    ]


# ---------------------------------------------------------------------------
# Scraper endpoints
# ---------------------------------------------------------------------------


class LearnBody(BaseModel):
    url: str


@app.post("/learn")
async def learn_from_url(body: LearnBody):
    report = await scraper_service.learn_from_url(body.url)
    return {
        "url": report.url,
        "tracks_found": report.tracks_found,
        "transitions_created": report.transitions_created,
        "success": report.success,
        "error": report.error,
    }


class ScrapeBody(BaseModel):
    genres: list[str] | None = None
    max_sets: int = 100


@app.post("/scrape")
async def run_scrape(body: ScrapeBody):
    if scraper_service.is_running:
        return {"error": "Crawl already in progress"}

    # Run as background task
    asyncio.create_task(_run_crawl(body.genres, body.max_sets))
    return {"status": "started", "genres": body.genres, "max_sets": body.max_sets}


async def _run_crawl(genres: list[str] | None, max_sets: int) -> None:
    report = await scraper_service.run_full_crawl(genres=genres, max_sets=max_sets)
    await admin_ws.broadcast({
        "type": "crawl_complete",
        "data": {
            "sets_discovered": report.sets_discovered,
            "sets_parsed": report.sets_parsed,
            "tracks_imported": report.tracks_imported,
            "transitions_created": report.transitions_created,
            "errors": report.errors,
        },
    })
