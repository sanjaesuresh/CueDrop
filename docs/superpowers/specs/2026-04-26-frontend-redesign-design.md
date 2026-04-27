# CueDrop Frontend Redesign — Design Spec

## Overview

Complete visual redesign of both admin and guest frontends. Replace the current dark-gray minimal prototype with a neon vibrant aesthetic — purple/pink/cyan accents on deep black. Restructure admin navigation from a flat tab bar to a home hub dashboard with push-on sub-screens.

No new npm dependencies. All styling via Tailwind CSS v4 classes. Existing WebSocket hooks, API calls, and backend endpoints are unchanged.

---

## Visual Identity

### Colors

| Role | Token | Hex | Usage |
|------|-------|-----|-------|
| Background (deep) | `bg-deep` | `#0c0a1a` | Page background |
| Background (card) | `bg-card` | `#1a0e2e` | Cards, panels |
| Background (surface) | `bg-surface` | `#221538` | Elevated elements, inputs |
| Purple (primary) | `purple-500/400` | `#8b5cf6 / #a78bfa` | Primary UI, queue, transitions, buttons |
| Pink (secondary) | `pink-500/400` | `#ec4899 / #f472b6` | Key data, guest requests, alert dots |
| Cyan (tertiary) | `cyan-400` | `#22d3ee` | Energy data, status indicators |
| Text primary | — | `#f8fafc` | Headings, track titles |
| Text secondary | — | `#c4b5fd` | Artist names, subtitles (purple-tinted) |
| Text muted | — | `#64748b` | Labels, timestamps |
| Border | — | `rgba(139,92,246,0.15–0.25)` | Card borders, dividers |

### Style Rules

- Card backgrounds use faint colored tints (`rgba(139,92,246,0.06–0.15)`), never flat gray
- Interactive elements get `box-shadow: 0 0 N px` glow in their accent color on hover/active
- Progress bars use `linear-gradient(90deg, #8b5cf6, #a78bfa)` with a purple glow shadow
- Borders on cards: `1px solid rgba(139,92,246,0.2)` — visible but subtle
- Border-radius: 16px for major cards, 12px for list items, 20px for pill badges
- Each data type has a dedicated color: BPM=purple, Key=pink, Energy=cyan

---

## Navigation Pattern: Home Hub

The admin home screen is the central dashboard. Other screens push on top with a back arrow in the header. No persistent tab bar or bottom navigation.

```
Home (default)
  ├── Queue (push)
  ├── Search (push)
  ├── Chat (push)
  └── Settings (push, includes QR/session management)
```

Navigation state managed via `useState` in `admin/App.jsx` — no React Router sub-routes needed. A simple `screen` state variable (`'home' | 'queue' | 'search' | 'chat' | 'settings'`).

---

## Admin Screens

### 1. Home (`Home.jsx` — NEW)

The DJ's primary view during a set. Everything important is visible at a glance.

**Layout (top to bottom):**

1. **Header row** — session name (left), QR icon + settings gear (right)
2. **Now Playing hero card** — gradient background (`rgba(purple, 0.15)` to `rgba(pink, 0.1)`), contains:
   - "Now Playing" label with pulsing dot
   - Track title (20px, bold) and artist (13px, purple-tinted)
   - Stats row: BPM (purple), Key (pink), Energy (cyan), timestamp (right-aligned)
   - Progress bar (gradient purple, glow shadow)
3. **Quick action row** — 3 equal buttons: Skip (pink), Search (purple), Chat (cyan, with pink notification dot when pending requests exist)
4. **Up Next section** — label "Up Next" with "View Queue →" link (taps to queue screen), shows first 2 queue entries with:
   - Track title + artist + BPM + key
   - Transition type badge (BLEND, CUT, etc.)
   - Left border color by layer

**Empty state:** When no track is playing, the hero card shows "No track playing" with a muted message and a prominent "Search for tracks" button.

**Data sources:**
- Now playing: `queueState.current` from WebSocket
- Up next: `queueState.entries[0..1]`
- Pending count: `pendingRequests.length` (for chat notification dot)

### 2. Queue (`QueuePanel.jsx` — RESTYLE)

**Header:** Back arrow + "Queue" title + entry count badge

**Content:** Scrollable list of all queue entries.

Each entry card:
- Left border: 3px, color by layer (locked=purple-500, anchor=purple-400, soft=purple-300/50, wildcard=amber, horizon=purple/20)
- Background: faint purple tint, decreasing opacity for lower layers
- Content: track title, artist, BPM + key + source badge
- Source badges: Admin (blue), Guest (green), AI (purple), Wildcard (amber)
- Transition type badge (right side): BLEND, BASS_SWAP, CUT, ECHO_OUT, FILTER_SWEEP
- Horizon layer entries at reduced opacity (0.5)

**Wildcards section:** Separated by a label "Wildcards" in amber, dashed border entries.

### 3. Search (`SearchPanel.jsx` — NEW)

**Header:** Back arrow + "Search" title

**Search input:** Full-width, `bg-surface` background, purple focus ring, placeholder "Search Spotify..."

**Results list:** Debounced search (300ms) against `GET /search?q=...&limit=10`. Each result:
- Music note icon (purple-tinted placeholder)
- Track title + artist
- Duration (right)
- Tap action: `POST /request/admin` with track data, then show success toast and remain on search screen

**Empty states:**
- No query: "Search for a song to add to the queue"
- No results: "No results found"
- Loading: pulsing "Searching..." text

### 4. Chat (`ChatPanel.jsx` — RESTYLE)

**Header:** Back arrow + "Chat" title + pending request count badge (pink)

**Message list:** Scrollable, newest at bottom.
- User messages: purple background (`bg-purple-700/60`), right-aligned
- AI messages: dark card background (`bg-card`), left-aligned, with intent badge (small pill)
- Typing indicator: pulsing dots in a dark card

**Approval cards** (inline in message flow):
- Pink-tinted border and background
- "Guest Request" label in pink
- Track title + artist
- Approve (green) / Decline (red) buttons
- Disabled state while processing

**Input bar:** Fixed at bottom, `bg-surface` input with purple focus ring, Send button (purple).

### 5. Settings (`Settings.jsx` — RESTYLE + MERGE SessionManager)

**Header:** Back arrow + "Settings" title

**Sections:**

1. **Session** — session name input, QR code display (inline, not a separate modal), "Download QR" button (purple), session ID display
2. **Guest Requests** — toggle for enabled/disabled, toggle for manual approval, cooldown minutes input
3. **Set** — set length input, energy arc selector (Club Night / Festival / Lounge)

All inputs: `bg-surface` background, purple focus ring, purple accent on checkboxes/toggles.

Save button: full-width, purple gradient, bottom of page.

---

## Guest Screens

### Search (`guest/Search.jsx` — RESTYLE)

Match the neon vibrant theme:
- Background: `bg-deep`
- Search input: `bg-surface`, purple focus ring
- Results: purple-tinted card backgrounds, same layout as admin search
- Tap to submit: calls `POST /request/guest`

### Confirmation (`guest/Confirmation.jsx` — RESTYLE)

- Background: `bg-deep`
- Track info centered with music icon in gradient box
- Status pills with glow effects:
  - Pending: amber background + amber glow + pulsing dot
  - Approved: green background + green glow + checkmark
  - Declined: red background + red glow
- ETA text below status
- Cooldown timer
- "Request Another Song" button: purple gradient

### Guest App (`guest/App.jsx` — RESTYLE)

- Header: session name in purple, now-playing subtitle
- Same deep black + purple-tinted background

---

## Component File Map

```
src/admin/
  App.jsx             — REWRITE: home hub + screen state management + WebSocket hook
  Home.jsx            — NEW: now playing hero + quick actions + up-next
  NowPlaying.jsx      — REWRITE: gradient card component used by Home
  QueuePanel.jsx      — RESTYLE: neon layer borders, source badges, transition badges
  SearchPanel.jsx     — NEW: Spotify search + admin track add
  ChatPanel.jsx       — RESTYLE: purple bubbles, better approval cards
  Settings.jsx        — RESTYLE + MERGE: absorb SessionManager, neon inputs, QR inline
  SessionManager.jsx  — DELETE: functionality merged into Settings
  GuestRequests.jsx   — DELETE: was already a no-op stub

src/guest/
  App.jsx             — RESTYLE: neon theme
  Search.jsx          — RESTYLE: neon theme
  Confirmation.jsx    — RESTYLE: neon theme with glowing status pills
```

**Files added:** 2 (Home.jsx, SearchPanel.jsx)
**Files deleted:** 2 (SessionManager.jsx, GuestRequests.jsx)
**Files rewritten:** 2 (admin/App.jsx, NowPlaying.jsx)
**Files restyled:** 5 (QueuePanel.jsx, ChatPanel.jsx, Settings.jsx, guest/App.jsx, guest/Search.jsx, guest/Confirmation.jsx)

---

## API Integration

No new endpoints needed. Existing endpoints used:

| Screen | Endpoint | Method |
|--------|----------|--------|
| Home (now playing) | `/ws/admin` | WebSocket (queue_update) |
| Home (pending count) | `/requests/pending` | GET (polling) |
| Home (skip) | `/skip` | POST |
| Queue | `/ws/admin` | WebSocket (queue_update) |
| Search | `/search?q=...&limit=N` | GET |
| Search (add track) | `/request/admin` | POST |
| Chat | `/chat` | POST |
| Chat (approvals) | `/approve/{id}`, `/decline/{id}` | POST |
| Chat (pending) | `/requests/pending` | GET |
| Settings (save) | `/settings` | PUT |
| Settings (QR) | `/session/qr` | GET |
| Settings (session) | `/session/current` | GET |
| Guest search | `/search?q=...` | GET |
| Guest request | `/request/guest` | POST |
| Guest session | `/session/{id}` | GET |
| Guest live | `/ws/guest/{id}` | WebSocket |

---

## Testing Plan

- Start dev server (`npm run dev`) and backend (`uvicorn`)
- Verify each admin screen renders with mock data (MockVDJ, no Neo4j needed)
- Test navigation: home → each sub-screen → back to home
- Test search: type query, see results, tap to add
- Test chat: send message, see response
- Test settings: change values, save
- Test guest flow: search → submit → confirmation screen
- Test on mobile viewport (375px width) in browser DevTools
- Test PWA install still works (manifest + service worker unchanged)
