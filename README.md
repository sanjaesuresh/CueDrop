# CueDrop -- AI-Powered DJ Assistant

CueDrop is an AI system that autonomously selects and transitions between tracks using a Neo4j transition graph learned from real DJ sets. It controls VirtualDJ over HTTP, plans harmonic and energy-aware transitions, and handles guest song requests submitted via QR code -- all managed through an admin chat interface powered by Claude.

---

## Architecture

```
GUEST PHONES (browser, no app install)
  |   Scan QR --> /guest/:session_id
  |   Spotify search --> submit request
  |   WebSocket /ws/guest/:id (confirmation + now playing)
  |         |
  |         | ngrok tunnel
  v         v
ADMIN PHONE (React PWA)
  |   /admin -- swipeable tabs: Queue | Chat
  |   Approval cards inline in chat
  |   Settings via gear icon
  |   WebSocket /ws/admin (live state + approvals)
  |         |
  |         | ngrok tunnel or local WiFi
  v         v
LAPTOP -- FastAPI Server (port 8000)
  |-- REST endpoints (queue, requests, chat, search, scraper)
  |-- WebSocket managers (admin + guest)
  |-- DJBrain (track selection + replanning)
  |-- QueueManager (5-layer priority queue)
  |-- TransitionPlanner (type selection + VDJscript generation)
  |-- ChatHandler (Claude API NLU)
  |-- GuestHandler (validation + approval + cooldown)
  |-- MusicResolver (Spotify --> Beatport/Tidal/local)
  |-- ScraperService (weekly cron + manual trigger)
  |-- AudioAnalysis (BPM, key, energy, mix points via librosa)
  |-- GraphClient (Neo4j async driver)
  |         |
  |         | HTTP
  v         v
VirtualDJ Pro (NetworkControlPlugin, localhost:80)

Neo4j (bolt://localhost:7687) -- transition knowledge graph
Essentia Service (port 8001) -- advanced audio feature extraction
```

---

## Tech Stack

| Layer        | Technology                                      |
|--------------|--------------------------------------------------|
| Frontend     | React 19, Vite 6, Tailwind CSS v4, React Router 7 |
| Backend      | FastAPI, Uvicorn, WebSockets, Pydantic v2        |
| AI / NLU     | Anthropic Claude API (chat intent parsing)       |
| Graph DB     | Neo4j 5 Community (with APOC plugin)             |
| Audio        | librosa (BPM/key/energy), Essentia (features)    |
| Playback     | VirtualDJ Pro via HTTP API                       |
| Music Search | Spotify Web API (search/metadata)                |
| Scraping     | yt-dlp, Playwright, BeautifulSoup, ACRCloud      |
| Infra        | Docker Compose, nginx                            |

---

## Features

- **Autonomous track selection** -- DJBrain scores candidates using transition frequency, harmonic compatibility (Camelot wheel), energy flow, and BPM proximity
- **5-layer priority queue** -- locked, soft, anchor, wildcard, and horizon layers give the AI room to plan ahead while respecting admin and guest picks
- **Transition planning** -- selects transition type (blend, cut, echo-out, backspin, etc.) and generates VDJscript commands with timing
- **Guest requests via QR** -- guests scan a QR code, search Spotify, and submit requests; per-device cooldowns and genre filters prevent abuse
- **Admin chat interface** -- natural language commands parsed by Claude (track requests, vibe shifts, energy changes, skips, queries)
- **Audio analysis pipeline** -- extracts BPM, musical key, energy, and mix-in/mix-out points from local audio files using librosa
- **Scraper pipeline** -- discovers DJ sets from the web, extracts tracklists, identifies transitions, and imports them into the Neo4j graph
- **Learning loop** -- logs transition quality signals (skips, overrides, full plays) and re-weights graph edges to improve future selections
- **Music resolution** -- resolves Spotify search results to playable sources (local library, Beatport Link, Tidal)

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Neo4j 5 (or Docker)
- VirtualDJ Pro with NetworkControlPlugin (optional for development -- a mock client is used when `VDJ_AUTH_TOKEN` is unset)

### Setup

```bash
# Clone the repository
git clone https://github.com/sanjaesuresh/CueDrop.git
cd CueDrop

# Backend
cd backend
cp .env.example .env          # Edit with your API keys
pip install -e ".[scraping]"  # Install with optional scraping deps
cd ..

# Frontend
npm install

# Start Neo4j (via Docker Compose)
docker compose up neo4j -d

# Run the backend server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Run the frontend dev server (separate terminal)
npm run dev
```

The admin UI will be available at `http://localhost:5173` and the API at `http://localhost:8000`.

### Docker Compose (full stack)

```bash
docker compose up --build
```

This starts Neo4j, the Essentia audio analysis service, the FastAPI backend, and the frontend (served via nginx).

---

## API Endpoints

### REST

| Method | Path                    | Description                          |
|--------|-------------------------|--------------------------------------|
| GET    | `/health`               | Health check                         |
| GET    | `/queue`                | Current queue state (all 5 layers)   |
| POST   | `/request/admin`        | Add a track as admin                 |
| POST   | `/request/guest`        | Submit a guest track request         |
| POST   | `/skip`                 | Skip current track                   |
| GET    | `/status`               | VirtualDJ deck statuses              |
| POST   | `/chat`                 | Send a chat message (Claude NLU)     |
| GET    | `/requests/pending`     | List pending guest requests          |
| POST   | `/approve/{request_id}` | Approve a guest request              |
| POST   | `/decline/{request_id}` | Decline a guest request              |
| GET    | `/session/qr`           | Generate session QR code (PNG)       |
| GET    | `/session/{session_id}` | Get session info and now playing     |
| PUT    | `/settings`             | Update session settings              |
| GET    | `/search?q=...&limit=N` | Search tracks via Spotify            |
| POST   | `/learn`                | Import transitions from a single URL |
| POST   | `/scrape`               | Start a background scraping crawl    |

### WebSocket

| Path                      | Description                              |
|---------------------------|------------------------------------------|
| `/ws/admin`               | Admin live updates (queue, approvals)    |
| `/ws/guest/{session_id}`  | Guest updates (confirmation, now playing)|

---

## Project Structure

```
cuedrop/
|-- backend/
|   |-- main.py                 # FastAPI app, endpoints, WebSocket managers
|   |-- config.py               # Settings loaded from .env
|   |-- models.py               # Pydantic models (Track, Transition, Queue, etc.)
|   |-- dj_brain.py             # Track selection scoring and replanning
|   |-- queue_manager.py        # 5-layer priority queue
|   |-- transition_planner.py   # Transition type selection + VDJscript generation
|   |-- orchestrator.py         # Ties together queue, brain, planner, VDJ, logger
|   |-- vdj_client.py           # VirtualDJ HTTP API wrapper + mock client
|   |-- chat_handler.py         # Claude API NLU for admin chat
|   |-- guest_handler.py        # Guest request validation, approval, cooldowns
|   |-- music_resolver.py       # Spotify search + playable source resolution
|   |-- graph_client.py         # Neo4j async driver wrapper
|   |-- audio_analysis.py       # BPM, key, energy extraction via librosa
|   |-- camelot.py              # Camelot wheel harmonic compatibility
|   |-- edge_reweighter.py      # Graph edge re-weighting (learning loop)
|   |-- transition_logger.py    # Transition quality signal collection
|   |-- scraper_service.py      # Scraping orchestrator for API use
|   |-- import_pipeline.py      # JSON import pipeline for knowledge base
|   |-- qr_generator.py         # Session QR code generation
|   |-- cli.py                  # CLI for scrape, import, stats, search
|   |-- Dockerfile              # Backend container image
|   |-- pyproject.toml          # Python dependencies
|   |-- tests/                  # Backend test suite
|   +-- fixtures/               # Test fixture data
|
|-- src/
|   |-- main.jsx                # React entry point
|   |-- App.jsx                 # App shell and routing
|   |-- admin/                  # Admin dashboard components
|   +-- guest/                  # Guest request UI components
|
|-- scraper/
|   |-- tracklist_scraper.py    # Tracklist extraction from DJ set pages
|   |-- youtube_scraper.py      # YouTube DJ set discovery
|   |-- transition_extractor.py # Transition identification from tracklists
|   +-- fingerprinter.py        # Audio fingerprinting (ACRCloud)
|
|-- essentia-service/
|   |-- Dockerfile              # Essentia container (x86 via Rosetta on ARM)
|   +-- server.py               # HTTP wrapper for Essentia audio analysis
|
|-- docker-compose.yml          # Neo4j, Essentia, backend, frontend
|-- Dockerfile.frontend         # Frontend container (nginx)
|-- nginx.conf                  # nginx config for frontend serving
|-- package.json                # Frontend dependencies
|-- vite.config.js              # Vite build configuration
+-- _docs/                      # Design documents and plans
```

---

## Configuration

Create `backend/.env` with the following variables:

```bash
# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=cuedrop_dev

# VirtualDJ (leave empty to use MockVDJClient)
VDJ_HOST=http://127.0.0.1:80
VDJ_AUTH_TOKEN=

# Anthropic (required for chat NLU)
ANTHROPIC_API_KEY=sk-ant-...

# Spotify (required for guest search)
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

# Local music library path
LOCAL_LIBRARY_PATH=/path/to/your/music

# ACRCloud (optional, for audio fingerprinting)
ACRCLOUD_ACCESS_KEY=
ACRCLOUD_ACCESS_SECRET=
ACRCLOUD_HOST=

# Server
HOST=0.0.0.0
PORT=8000
```
