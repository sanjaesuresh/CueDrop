# Frontend Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the prototype admin and guest UIs with a polished neon vibrant design — purple/pink/cyan on deep black, home hub navigation, Spotify search for admin.

**Architecture:** Frontend-only change. 10 React component files (2 new, 2 rewritten, 6 restyled, 2 deleted). Custom Tailwind v4 theme colors via `@theme` in CSS. Navigation via `useState` screen switching in admin/App.jsx. All existing API endpoints and WebSocket hooks reused as-is.

**Tech Stack:** React 19, Tailwind CSS v4, Vite 6

**Spec:** `docs/superpowers/specs/2026-04-26-frontend-redesign-design.md`

---

## File Map

```
MODIFY  src/index.css              — Add @theme with custom colors, remove App.css import
DELETE  src/App.css                 — Remove default Vite styles (conflicts with Tailwind)
MODIFY  vite.config.js             — Add proxy rules for backend API paths

REWRITE src/admin/App.jsx          — Home hub + screen state + WebSocket hook
CREATE  src/admin/Home.jsx         — Now playing hero + quick actions + up-next
REWRITE src/admin/NowPlaying.jsx   — Gradient card component
RESTYLE src/admin/QueuePanel.jsx   — Neon layer borders, source badges
CREATE  src/admin/SearchPanel.jsx  — Spotify search + admin track add
RESTYLE src/admin/ChatPanel.jsx    — Purple bubbles, approval cards
RESTYLE src/admin/Settings.jsx     — Merge SessionManager, neon inputs, QR inline
DELETE  src/admin/SessionManager.jsx
DELETE  src/admin/GuestRequests.jsx

RESTYLE src/guest/App.jsx          — Neon theme
RESTYLE src/guest/Search.jsx       — Neon theme
RESTYLE src/guest/Confirmation.jsx — Neon theme with glowing status pills
```

---

### Task 1: Theme CSS + Vite Config

**Files:**
- Modify: `src/index.css`
- Delete: `src/App.css`
- Modify: `src/main.jsx` (remove App.css import if present)
- Modify: `vite.config.js`

- [ ] **Step 1: Replace `src/index.css` with Tailwind v4 theme**

```css
@import "tailwindcss";

@theme {
  --color-deep: #0c0a1a;
  --color-card: #1a0e2e;
  --color-surface: #221538;
}
```

This gives us `bg-deep`, `bg-card`, `bg-surface` as Tailwind classes.

- [ ] **Step 2: Delete `src/App.css`**

Delete the file entirely — its global `h1`, `button`, `.card` styles conflict with Tailwind.

- [ ] **Step 3: Remove App.css import from `src/main.jsx` if present**

Check if `main.jsx` imports `App.css`. If it does, remove that import line. Currently it only imports `./index.css`, so this may be a no-op.

- [ ] **Step 4: Update Vite proxy config**

Replace `vite.config.js` with:

```js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
      '/health': 'http://localhost:8000',
      '/queue': 'http://localhost:8000',
      '/request': 'http://localhost:8000',
      '/skip': 'http://localhost:8000',
      '/tick': 'http://localhost:8000',
      '/status': 'http://localhost:8000',
      '/chat': 'http://localhost:8000',
      '/requests': 'http://localhost:8000',
      '/approve': 'http://localhost:8000',
      '/decline': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/search': 'http://localhost:8000',
      '/learn': 'http://localhost:8000',
      '/scrape': 'http://localhost:8000',
    },
  },
});
```

- [ ] **Step 5: Commit**

```
feat: add neon theme colors and fix vite proxy config
```

---

### Task 2: Admin App.jsx — Home Hub Shell

**Files:**
- Rewrite: `src/admin/App.jsx`

- [ ] **Step 1: Rewrite `src/admin/App.jsx`**

```jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import Home from './Home.jsx';
import QueuePanel from './QueuePanel.jsx';
import SearchPanel from './SearchPanel.jsx';
import ChatPanel from './ChatPanel.jsx';
import Settings from './Settings.jsx';

function useAdminWebSocket(onMessage) {
  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);

  const connect = useCallback(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws/admin`);
    ws.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)); } catch {}
    };
    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connect, 2000);
    };
    ws.onerror = () => ws.close();
    wsRef.current = ws;
  }, [onMessage]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);
}

function BackHeader({ title, onBack, badge }) {
  return (
    <header className="flex items-center gap-3 px-4 py-3 border-b border-purple-500/15">
      <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-surface transition-colors">
        <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>
      <h1 className="text-lg font-bold text-white flex-1">{title}</h1>
      {badge != null && badge > 0 && (
        <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-pink-500/20 text-pink-400 border border-pink-500/30">
          {badge}
        </span>
      )}
    </header>
  );
}

export default function AdminApp() {
  const [screen, setScreen] = useState('home');
  const [queueState, setQueueState] = useState({ current: null, entries: [], wildcards: [] });
  const [pendingRequests, setPendingRequests] = useState([]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'queue_update') {
      setQueueState(msg.data);
    }
  }, []);

  useAdminWebSocket(handleWsMessage);

  useEffect(() => {
    fetch('/requests/pending').then(r => r.json()).then(setPendingRequests).catch(() => {});
    const interval = setInterval(() => {
      fetch('/requests/pending').then(r => r.json()).then(setPendingRequests).catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-deep text-white">
      {screen === 'home' && (
        <Home
          queueState={queueState}
          pendingCount={pendingRequests.length}
          onNavigate={setScreen}
        />
      )}

      {screen === 'queue' && (
        <>
          <BackHeader title="Queue" onBack={() => setScreen('home')} badge={queueState.entries.length} />
          <main className="flex-1 overflow-hidden">
            <QueuePanel queueState={queueState} />
          </main>
        </>
      )}

      {screen === 'search' && (
        <>
          <BackHeader title="Search" onBack={() => setScreen('home')} />
          <main className="flex-1 overflow-hidden">
            <SearchPanel />
          </main>
        </>
      )}

      {screen === 'chat' && (
        <>
          <BackHeader title="Chat" onBack={() => setScreen('home')} badge={pendingRequests.length} />
          <main className="flex-1 overflow-hidden">
            <ChatPanel pendingRequests={pendingRequests} onRefreshRequests={() => {
              fetch('/requests/pending').then(r => r.json()).then(setPendingRequests).catch(() => {});
            }} />
          </main>
        </>
      )}

      {screen === 'settings' && (
        <>
          <BackHeader title="Settings" onBack={() => setScreen('home')} />
          <main className="flex-1 overflow-hidden">
            <Settings />
          </main>
        </>
      )}
    </div>
  );
}
```

Key changes from old App.jsx:
- `screen` state replaces `tab` state — supports 5 screens instead of 2 tabs
- `BackHeader` reusable component for sub-screens
- No more `showSettings` / `showSession` modals — Settings is a full screen
- Removed imports for deleted SessionManager and old NowPlaying (NowPlaying now used inside Home)
- `pendingCount` passed to Home for chat notification dot

- [ ] **Step 2: Commit**

```
feat: rewrite admin App.jsx with home hub navigation
```

---

### Task 3: NowPlaying Hero Card

**Files:**
- Rewrite: `src/admin/NowPlaying.jsx`

- [ ] **Step 1: Rewrite `src/admin/NowPlaying.jsx`**

```jsx
export default function NowPlaying({ current, onSearchClick }) {
  if (!current) {
    return (
      <div className="mx-3 rounded-2xl p-6 border border-purple-500/20 bg-gradient-to-br from-purple-500/10 to-pink-500/5">
        <p className="text-center text-slate-400 text-sm mb-3">No track playing</p>
        {onSearchClick && (
          <button
            onClick={onSearchClick}
            className="mx-auto block px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-sm font-medium transition-colors shadow-[0_0_12px_rgba(139,92,246,0.3)]"
          >
            Search for tracks
          </button>
        )}
      </div>
    );
  }

  const { track } = current;

  return (
    <div className="mx-3 rounded-2xl p-4 border border-purple-500/20 bg-gradient-to-br from-purple-500/15 to-pink-500/8 relative overflow-hidden">
      {/* Glow accent */}
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl pointer-events-none" />

      {/* Label */}
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_#a78bfa] animate-pulse" />
        <span className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold">Now Playing</span>
      </div>

      {/* Track info */}
      <h2 className="text-xl font-extrabold text-white leading-tight">{track.title}</h2>
      <p className="text-sm text-purple-300 mt-0.5">{track.artist}</p>

      {/* Stats row */}
      <div className="flex items-end gap-4 mt-3">
        <div>
          <div className="text-[9px] text-purple-500 uppercase tracking-wide">BPM</div>
          <div className="text-lg font-bold text-white">{track.bpm || '—'}</div>
        </div>
        <div>
          <div className="text-[9px] text-pink-500 uppercase tracking-wide">Key</div>
          <div className="text-lg font-bold text-white">{track.key || '—'}</div>
        </div>
        <div>
          <div className="text-[9px] text-cyan-400 uppercase tracking-wide">Energy</div>
          <div className="text-lg font-bold text-white">{track.energy || '—'}</div>
        </div>
        {track.duration_ms && (
          <div className="ml-auto text-xs text-slate-500">
            {Math.floor(track.duration_ms / 60000)}:{String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, '0')}
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div className="mt-2 h-[3px] bg-purple-500/15 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-purple-400 shadow-[0_0_6px_rgba(139,92,246,0.4)] animate-pulse"
          style={{ width: '45%' }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: rewrite NowPlaying as neon gradient hero card
```

---

### Task 4: Home Screen

**Files:**
- Create: `src/admin/Home.jsx`

- [ ] **Step 1: Create `src/admin/Home.jsx`**

```jsx
import NowPlaying from './NowPlaying.jsx';

const LAYER_BORDER = {
  locked: 'border-l-purple-500',
  anchor: 'border-l-purple-400',
  soft: 'border-l-purple-400/40',
  wildcard: 'border-l-amber-400',
  horizon: 'border-l-purple-500/20',
};

function UpNextEntry({ entry }) {
  const { track, layer, transition_plan } = entry;
  const border = LAYER_BORDER[layer] || 'border-l-purple-500/20';

  return (
    <div className={`rounded-xl px-3 py-2.5 bg-purple-500/[0.06] border-l-[3px] ${border}`}>
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{track.title}</p>
          <p className="text-xs text-slate-500 truncate">
            {track.artist}
            {track.bpm && <> · {track.bpm} BPM</>}
            {track.key && <> · {track.key}</>}
          </p>
        </div>
        {transition_plan?.type && (
          <span className="ml-2 px-2 py-0.5 text-[9px] font-semibold uppercase rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 shrink-0">
            {transition_plan.type}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Home({ queueState, pendingCount, onNavigate }) {
  const { current, entries } = queueState;
  const upNext = entries.slice(0, 2);

  const handleSkip = async () => {
    try { await fetch('/skip', { method: 'POST' }); } catch {}
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3">
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest">Session</p>
          <h1 className="text-base font-bold text-white">CueDrop</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onNavigate('settings')}
            className="p-2 rounded-lg hover:bg-surface transition-colors"
            title="Settings"
          >
            <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </header>

      {/* Now Playing hero */}
      <div className="mt-1">
        <NowPlaying current={current} onSearchClick={() => onNavigate('search')} />
      </div>

      {/* Quick actions */}
      <div className="flex gap-2 px-3 mt-3">
        <button
          onClick={handleSkip}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-pink-500/[0.08] border border-pink-500/15 hover:bg-pink-500/15 transition-colors active:scale-[0.97]"
        >
          <svg className="w-5 h-5 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v14" />
          </svg>
          <span className="text-[10px] text-pink-400 font-medium">Skip</span>
        </button>
        <button
          onClick={() => onNavigate('search')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-500/[0.08] border border-purple-500/15 hover:bg-purple-500/15 transition-colors active:scale-[0.97]"
        >
          <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span className="text-[10px] text-purple-400 font-medium">Search</span>
        </button>
        <button
          onClick={() => onNavigate('chat')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-cyan-400/[0.08] border border-cyan-400/15 hover:bg-cyan-400/15 transition-colors active:scale-[0.97] relative"
        >
          <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-[10px] text-cyan-400 font-medium">Chat</span>
          {pendingCount > 0 && (
            <span className="absolute top-1.5 right-[calc(50%-16px)] w-2 h-2 bg-pink-500 rounded-full shadow-[0_0_6px_#ec4899]" />
          )}
        </button>
      </div>

      {/* Up Next */}
      <div className="px-3 mt-4 flex-1">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Up Next</span>
          <button
            onClick={() => onNavigate('queue')}
            className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
          >
            View Queue →
          </button>
        </div>
        {upNext.length === 0 ? (
          <p className="text-sm text-slate-600 text-center py-6">Queue is empty</p>
        ) : (
          <div className="space-y-2">
            {upNext.map((entry, i) => (
              <UpNextEntry key={i} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: add Home hub screen with now playing, quick actions, and up-next
```

---

### Task 5: QueuePanel Restyle

**Files:**
- Restyle: `src/admin/QueuePanel.jsx`

- [ ] **Step 1: Rewrite `src/admin/QueuePanel.jsx`**

```jsx
const LAYER_STYLES = {
  locked: 'bg-purple-500/10 border-l-[3px] border-l-purple-500',
  anchor: 'bg-purple-500/[0.07] border-l-[3px] border-l-purple-400',
  soft: 'bg-purple-500/[0.04] border-l-[3px] border-l-purple-400/40',
  wildcard: 'bg-amber-500/[0.06] border border-dashed border-amber-500/30',
  horizon: 'bg-purple-500/[0.03] border-l-[3px] border-l-purple-500/20 opacity-50',
};

const SOURCE_BADGES = {
  admin: { label: 'Admin', cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  guest: { label: 'Guest', cls: 'bg-green-500/20 text-green-400 border-green-500/30' },
  ai: { label: 'AI', cls: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  wildcard: { label: 'Wild', cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

function QueueEntry({ entry }) {
  const { track, layer, source, transition_plan } = entry;
  const layerStyle = LAYER_STYLES[layer] || 'bg-card';
  const badge = SOURCE_BADGES[source] || SOURCE_BADGES.ai;

  return (
    <div className={`px-3 py-2.5 rounded-xl ${layerStyle}`}>
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{track.title}</p>
          <p className="text-xs text-slate-500 truncate">{track.artist}</p>
        </div>
        <div className="flex items-center gap-1.5 ml-2 shrink-0">
          {track.bpm && <span className="text-[10px] text-purple-500">{track.bpm}</span>}
          {track.key && <span className="text-[10px] text-pink-500">{track.key}</span>}
          <span className={`px-1.5 py-0.5 text-[9px] font-semibold rounded border ${badge.cls}`}>
            {badge.label}
          </span>
          {transition_plan?.type && (
            <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">
              {transition_plan.type.toUpperCase()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function QueuePanel({ queueState }) {
  const { entries, wildcards } = queueState;

  return (
    <div className="h-full overflow-y-auto p-3 space-y-2">
      {entries.length === 0 && wildcards.length === 0 && (
        <p className="text-center text-slate-600 text-sm py-12">Queue is empty</p>
      )}

      {entries.map((entry, i) => (
        <QueueEntry key={`e-${i}`} entry={entry} />
      ))}

      {wildcards.length > 0 && (
        <>
          <p className="text-[10px] text-amber-400 uppercase tracking-widest font-semibold mt-4 px-1">
            Wildcards
          </p>
          {wildcards.map((entry, i) => (
            <QueueEntry key={`w-${i}`} entry={entry} />
          ))}
        </>
      )}
    </div>
  );
}
```

Note: Removed `NowPlaying` import — NowPlaying is now rendered in Home.jsx, not in QueuePanel.

- [ ] **Step 2: Commit**

```
feat: restyle QueuePanel with neon borders and source badges
```

---

### Task 6: SearchPanel (New)

**Files:**
- Create: `src/admin/SearchPanel.jsx`

- [ ] **Step 1: Create `src/admin/SearchPanel.jsx`**

```jsx
import { useState, useRef, useEffect } from 'react';

export default function SearchPanel() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/search?q=${encodeURIComponent(query)}&limit=10`);
        const data = await res.json();
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const addTrack = async (track) => {
    try {
      await fetch('/request/admin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: track.title, artist: track.artist }),
      });
      setToast(`Added "${track.title}"`);
      setTimeout(() => setToast(null), 2000);
    } catch {
      setToast('Failed to add track');
      setTimeout(() => setToast(null), 2000);
    }
  };

  const formatDuration = (ms) => {
    if (!ms) return '';
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Toast */}
      {toast && (
        <div className="absolute top-2 left-4 right-4 z-10 px-4 py-2 bg-purple-600/90 backdrop-blur rounded-xl text-sm text-white text-center shadow-[0_0_15px_rgba(139,92,246,0.3)] animate-pulse">
          {toast}
        </div>
      )}

      {/* Search input */}
      <div className="p-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Spotify..."
          autoFocus
          className="w-full px-4 py-3 bg-surface rounded-xl text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-purple-500/50 text-sm border border-purple-500/10"
        />
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {!query.trim() && (
          <p className="text-center text-slate-600 text-sm mt-12">Search for a song to add to the queue</p>
        )}

        {loading && (
          <div className="text-center text-purple-400 text-sm mt-8 animate-pulse">Searching...</div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-1.5">
            {results.map((track) => (
              <button
                key={track.spotify_id}
                onClick={() => addTrack(track)}
                className="w-full flex items-center gap-3 p-3 bg-purple-500/[0.04] hover:bg-purple-500/10 rounded-xl text-left active:scale-[0.98] transition-all border border-transparent hover:border-purple-500/15"
              >
                <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{track.title}</p>
                  <p className="text-xs text-slate-500 truncate">{track.artist}</p>
                </div>
                <span className="text-xs text-slate-600 shrink-0">{formatDuration(track.duration_ms)}</span>
              </button>
            ))}
          </div>
        )}

        {!loading && query.trim() && results.length === 0 && (
          <p className="text-center text-slate-600 text-sm mt-8">No results found</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: add admin SearchPanel with Spotify search and track add
```

---

### Task 7: ChatPanel Restyle

**Files:**
- Restyle: `src/admin/ChatPanel.jsx`

- [ ] **Step 1: Rewrite `src/admin/ChatPanel.jsx`**

```jsx
import { useState, useRef, useEffect } from 'react';

function ApprovalCard({ request, onRefresh }) {
  const [acting, setActing] = useState(false);

  const handleAction = async (action) => {
    setActing(true);
    try {
      await fetch(`/${action}/${request.id}`, { method: 'POST' });
      onRefresh();
    } catch {} finally {
      setActing(false);
    }
  };

  return (
    <div className="rounded-xl p-3 bg-pink-500/[0.06] border border-pink-500/20">
      <p className="text-[10px] text-pink-400 font-semibold uppercase tracking-widest mb-1">Guest Request</p>
      <p className="text-sm font-medium text-white">{request.track?.title}</p>
      <p className="text-xs text-slate-500">{request.track?.artist}</p>
      <div className="flex gap-2 mt-2.5">
        <button
          disabled={acting}
          onClick={() => handleAction('approve')}
          className="flex-1 py-1.5 text-xs font-medium rounded-lg bg-green-500/15 text-green-400 border border-green-500/20 hover:bg-green-500/25 disabled:opacity-40 transition-colors"
        >
          Approve
        </button>
        <button
          disabled={acting}
          onClick={() => handleAction('decline')}
          className="flex-1 py-1.5 text-xs font-medium rounded-lg bg-red-500/15 text-red-400 border border-red-500/20 hover:bg-red-500/25 disabled:opacity-40 transition-colors"
        >
          Decline
        </button>
      </div>
    </div>
  );
}

export default function ChatPanel({ pendingRequests, onRefreshRequests }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setSending(true);

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: data.response, intent: data.intent },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: 'ai', text: 'Failed to get response.' }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {pendingRequests.map((req) => (
          <ApprovalCard key={req.id} request={req} onRefresh={onRefreshRequests} />
        ))}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
              msg.role === 'user'
                ? 'bg-purple-600/40 text-white border border-purple-500/20'
                : 'bg-card text-slate-200 border border-purple-500/10'
            }`}>
              {msg.intent && (
                <span className="inline-block px-1.5 py-0.5 text-[9px] font-semibold bg-purple-500/15 text-purple-400 rounded border border-purple-500/20 mb-1 mr-1">
                  {msg.intent}
                </span>
              )}
              {msg.text}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-card text-purple-400 px-3 py-2 rounded-xl text-sm border border-purple-500/10">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-purple-500/10 bg-deep">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Tell the AI DJ..."
            className="flex-1 px-3 py-2.5 bg-surface rounded-xl text-sm text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-purple-500/50 border border-purple-500/10"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="px-4 py-2.5 bg-purple-600 rounded-xl text-sm font-medium hover:bg-purple-500 disabled:opacity-40 transition-colors shadow-[0_0_10px_rgba(139,92,246,0.2)]"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: restyle ChatPanel with neon purple theme and better approval cards
```

---

### Task 8: Settings (Restyle + Merge SessionManager)

**Files:**
- Restyle: `src/admin/Settings.jsx`
- Delete: `src/admin/SessionManager.jsx`
- Delete: `src/admin/GuestRequests.jsx`

- [ ] **Step 1: Rewrite `src/admin/Settings.jsx`**

```jsx
import { useState, useEffect } from 'react';

const DEFAULTS = {
  session_name: 'My Set',
  guest_requests_enabled: true,
  manual_approval: true,
  cooldown_mins: 15,
  set_length_mins: 120,
  energy_arc: 'club_night',
};

export default function Settings() {
  const [values, setValues] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [qrUrl, setQrUrl] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);

  useEffect(() => {
    // Load QR and session info
    fetch('/session/qr').then(r => r.blob()).then(b => setQrUrl(URL.createObjectURL(b))).catch(() => {});
    fetch('/session/current').then(r => r.json()).then(setSessionInfo).catch(() => {});
    return () => { if (qrUrl) URL.revokeObjectURL(qrUrl); };
  }, []);

  const update = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  const save = async () => {
    setSaving(true);
    try {
      await fetch('/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
    } catch {} finally {
      setSaving(false);
    }
  };

  const inputCls = "mt-1 w-full px-3 py-2.5 bg-surface rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-purple-500/50 border border-purple-500/10";

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      {/* Session section */}
      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Session</h3>
        <label className="block mb-3">
          <span className="text-xs text-slate-400">Session Name</span>
          <input value={values.session_name} onChange={(e) => update('session_name', e.target.value)} className={inputCls} />
        </label>

        {/* QR Code inline */}
        {qrUrl && (
          <div className="flex flex-col items-center p-4 bg-card rounded-2xl border border-purple-500/15">
            <div className="bg-white p-3 rounded-xl mb-3">
              <img src={qrUrl} alt="Session QR" className="w-36 h-36" />
            </div>
            <p className="text-xs text-slate-500 text-center mb-2">Guests scan to request songs</p>
            <button
              onClick={() => {
                const a = document.createElement('a');
                a.href = qrUrl;
                a.download = 'cuedrop-qr.png';
                a.click();
              }}
              className="w-full py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-sm font-medium rounded-xl border border-purple-500/20 transition-colors"
            >
              Download QR
            </button>
          </div>
        )}

        {sessionInfo && (
          <div className="mt-3 px-3 py-2 bg-card rounded-xl border border-purple-500/10">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Session ID</span>
              <span className="text-slate-600 font-mono">{sessionInfo.id?.slice(0, 8)}</span>
            </div>
          </div>
        )}
      </section>

      {/* Guest Requests section */}
      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Guest Requests</h3>
        <label className="flex items-center justify-between py-2">
          <span className="text-sm text-slate-300">Requests Enabled</span>
          <input
            type="checkbox"
            checked={values.guest_requests_enabled}
            onChange={(e) => update('guest_requests_enabled', e.target.checked)}
            className="w-4 h-4 accent-purple-500 rounded"
          />
        </label>
        <label className="flex items-center justify-between py-2">
          <span className="text-sm text-slate-300">Manual Approval</span>
          <input
            type="checkbox"
            checked={values.manual_approval}
            onChange={(e) => update('manual_approval', e.target.checked)}
            className="w-4 h-4 accent-purple-500 rounded"
          />
        </label>
        <label className="block mt-2">
          <span className="text-xs text-slate-400">Cooldown (mins)</span>
          <input type="number" min={1} value={values.cooldown_mins} onChange={(e) => update('cooldown_mins', +e.target.value)} className={inputCls} />
        </label>
      </section>

      {/* Set section */}
      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Set</h3>
        <label className="block mb-3">
          <span className="text-xs text-slate-400">Set Length (mins)</span>
          <input type="number" min={10} value={values.set_length_mins} onChange={(e) => update('set_length_mins', +e.target.value)} className={inputCls} />
        </label>
        <label className="block">
          <span className="text-xs text-slate-400">Energy Arc</span>
          <select value={values.energy_arc} onChange={(e) => update('energy_arc', e.target.value)} className={inputCls}>
            <option value="club_night">Club Night</option>
            <option value="festival">Festival</option>
            <option value="lounge">Lounge</option>
          </select>
        </label>
      </section>

      {/* Save */}
      <button
        onClick={save}
        disabled={saving}
        className="w-full py-3 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium disabled:opacity-40 transition-colors shadow-[0_0_12px_rgba(139,92,246,0.25)]"
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
```

Note: `onClose` prop removed — Settings is now a full screen navigated via back arrow in App.jsx, not a modal overlay.

- [ ] **Step 2: Delete `src/admin/SessionManager.jsx` and `src/admin/GuestRequests.jsx`**

Both files are no longer imported. SessionManager functionality is now in Settings. GuestRequests was already a no-op stub.

- [ ] **Step 3: Commit**

```
feat: restyle Settings with neon theme, merge SessionManager, delete stubs
```

---

### Task 9: Guest App Restyle

**Files:**
- Restyle: `src/guest/App.jsx`

- [ ] **Step 1: Rewrite `src/guest/App.jsx`**

```jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import Search from './Search.jsx';
import Confirmation from './Confirmation.jsx';

function getDeviceId() {
  let id = sessionStorage.getItem('cuedrop_device_id');
  if (!id) {
    id = crypto.randomUUID();
    sessionStorage.setItem('cuedrop_device_id', id);
  }
  return id;
}

export default function GuestApp() {
  const { sessionId } = useParams();
  const [sessionInfo, setSessionInfo] = useState(null);
  const [view, setView] = useState('search');
  const [submittedRequest, setSubmittedRequest] = useState(null);
  const [nowPlaying, setNowPlaying] = useState(null);
  const wsRef = useRef(null);
  const deviceId = useRef(getDeviceId());

  useEffect(() => {
    fetch(`/session/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        setSessionInfo(data);
        if (data.now_playing) setNowPlaying(data.now_playing);
      })
      .catch(() => {});
  }, [sessionId]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'now_playing') setNowPlaying(msg.data);
    if (msg.type === 'request_update' && submittedRequest) {
      setSubmittedRequest((prev) => ({ ...prev, ...msg.data }));
    }
  }, [submittedRequest]);

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${location.host}/ws/guest/${sessionId}`);
    ws.onmessage = (e) => {
      try { handleWsMessage(JSON.parse(e.data)); } catch {}
    };
    ws.onclose = () => setTimeout(() => {}, 3000);
    wsRef.current = ws;
    return () => ws.close();
  }, [sessionId, handleWsMessage]);

  const handleSelect = async (track) => {
    try {
      const res = await fetch('/request/guest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          track: { title: track.title, artist: track.artist },
          session_id: sessionId,
          device_id: deviceId.current,
        }),
      });
      const data = await res.json();
      setSubmittedRequest({ ...data, track });
      setView('confirmation');
    } catch {
      alert('Failed to submit request. Try again.');
    }
  };

  return (
    <div className="flex flex-col h-screen bg-deep text-white">
      {/* Header */}
      <header className="px-4 py-3 border-b border-purple-500/10">
        <h1 className="text-lg font-bold text-purple-400">
          {sessionInfo?.name || 'CueDrop'}
        </h1>
        {nowPlaying && (
          <p className="text-xs text-slate-500 mt-0.5">
            Now playing: <span className="text-slate-400">{nowPlaying.track?.title}</span> — {nowPlaying.track?.artist}
          </p>
        )}
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {view === 'search' && <Search onSelect={handleSelect} />}
        {view === 'confirmation' && (
          <Confirmation
            request={submittedRequest}
            onRequestAnother={() => { setView('search'); setSubmittedRequest(null); }}
          />
        )}
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: restyle guest App with neon theme
```

---

### Task 10: Guest Search Restyle

**Files:**
- Restyle: `src/guest/Search.jsx`

- [ ] **Step 1: Rewrite `src/guest/Search.jsx`**

```jsx
import { useState, useRef, useEffect } from 'react';

export default function Search({ onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim()) {
      setResults([]);
      return;
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/search?q=${encodeURIComponent(query)}&limit=10`);
        const data = await res.json();
        setResults(data);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  const formatDuration = (ms) => {
    if (!ms) return '';
    const mins = Math.floor(ms / 60000);
    const secs = Math.floor((ms % 60000) / 1000);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a song..."
          autoFocus
          className="w-full px-4 py-3 bg-surface rounded-xl text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-purple-500/50 text-base border border-purple-500/10"
        />
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {!query.trim() && (
          <p className="text-center text-slate-600 text-sm mt-12">Search for a song to request</p>
        )}

        {loading && (
          <div className="text-center text-purple-400 text-sm mt-8 animate-pulse">Searching...</div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-1.5">
            {results.map((track) => (
              <button
                key={track.spotify_id}
                onClick={() => onSelect(track)}
                className="w-full flex items-center gap-3 p-3 bg-purple-500/[0.04] hover:bg-purple-500/10 rounded-xl text-left active:scale-[0.98] transition-all border border-transparent hover:border-purple-500/15"
              >
                <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{track.title}</p>
                  <p className="text-xs text-slate-500 truncate">{track.artist}</p>
                </div>
                <span className="text-xs text-slate-600 shrink-0">{formatDuration(track.duration_ms)}</span>
              </button>
            ))}
          </div>
        )}

        {!loading && query.trim() && results.length === 0 && (
          <p className="text-center text-slate-600 text-sm mt-8">No results found</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: restyle guest Search with neon theme
```

---

### Task 11: Guest Confirmation Restyle

**Files:**
- Restyle: `src/guest/Confirmation.jsx`

- [ ] **Step 1: Rewrite `src/guest/Confirmation.jsx`**

```jsx
import { useState, useEffect } from 'react';

export default function Confirmation({ request, onRequestAnother }) {
  const [cooldownLeft, setCooldownLeft] = useState(0);

  useEffect(() => {
    if (!request) return;
    const cooldownMs = 15 * 60 * 1000;
    const submittedAt = new Date(request.submitted_at || Date.now()).getTime();
    const endTime = submittedAt + cooldownMs;

    const tick = () => setCooldownLeft(Math.max(0, endTime - Date.now()));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [request]);

  if (!request) return null;

  const { status, track } = request;
  const cooldownActive = cooldownLeft > 0;
  const cooldownMins = Math.floor(cooldownLeft / 60000);
  const cooldownSecs = Math.floor((cooldownLeft % 60000) / 1000);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Track icon */}
      <div className="w-20 h-20 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl flex items-center justify-center mb-4 border border-purple-500/20 shadow-[0_0_20px_rgba(139,92,246,0.15)]">
        <svg className="w-10 h-10 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
        </svg>
      </div>

      <h2 className="text-lg font-bold text-white text-center">{track?.title}</h2>
      <p className="text-sm text-purple-300 text-center">{track?.artist}</p>

      {/* Status */}
      <div className="mt-6 w-full max-w-xs">
        {status === 'pending' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-full shadow-[0_0_12px_rgba(245,158,11,0.15)]">
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse shadow-[0_0_6px_#f59e0b]" />
              <span className="text-sm text-amber-300">Waiting for approval</span>
            </div>
          </div>
        )}

        {status === 'approved' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-500/10 border border-green-500/20 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.15)]">
              <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-green-300">Approved!</span>
            </div>
            {request.eta_mins && (
              <p className="text-xs text-slate-500 mt-2">
                Estimated play time: ~{Math.round(request.eta_mins)} min
              </p>
            )}
          </div>
        )}

        {status === 'declined' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-500/10 border border-red-500/20 rounded-full shadow-[0_0_12px_rgba(239,68,68,0.15)]">
              <span className="text-sm text-red-300">Request declined</span>
            </div>
            {request.decline_reason && (
              <p className="text-xs text-slate-500 mt-2">{request.decline_reason}</p>
            )}
          </div>
        )}
      </div>

      {/* Cooldown + Request Another */}
      <div className="mt-8 w-full max-w-xs">
        {cooldownActive && (
          <p className="text-center text-xs text-slate-600 mb-3">
            You can request again in {cooldownMins}:{cooldownSecs.toString().padStart(2, '0')}
          </p>
        )}
        <button
          onClick={onRequestAnother}
          disabled={cooldownActive}
          className="w-full py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-surface disabled:text-slate-600 rounded-xl text-sm font-medium transition-colors shadow-[0_0_12px_rgba(139,92,246,0.25)] disabled:shadow-none"
        >
          Request Another Song
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```
feat: restyle guest Confirmation with neon glowing status pills
```

---

### Task 12: Visual Verification

- [ ] **Step 1: Start the dev server**

```bash
npm run dev
```

- [ ] **Step 2: Open admin UI in browser at `http://localhost:5173/admin`**

Verify:
- Home screen renders with deep black background and purple-tinted cards
- Now Playing hero card shows gradient background (or empty state with "Search for tracks" button)
- Quick action buttons (Skip, Search, Chat) are visible with correct accent colors
- Up Next section shows "Queue is empty" or queue entries

- [ ] **Step 3: Test navigation**

Click each quick action button and verify:
- Search → shows search input, back arrow works
- Chat → shows chat input, back arrow works
- Queue (via "View Queue →") → shows queue list, back arrow works
- Settings (via gear icon) → shows settings with QR section, back arrow works

- [ ] **Step 4: Open guest UI at `http://localhost:5173/guest/test-session`**

Verify:
- Deep black background with purple-tinted header
- Search input with purple focus ring
- Search results (if backend is running) with purple-tinted cards

- [ ] **Step 5: Test mobile viewport**

Open browser DevTools, set viewport to 375x812 (iPhone). Verify:
- All screens fit without horizontal scroll
- Touch targets are large enough (min 44px)
- Text is readable

- [ ] **Step 6: Final commit (if any fixes needed)**

```
fix: visual tweaks from verification
```
