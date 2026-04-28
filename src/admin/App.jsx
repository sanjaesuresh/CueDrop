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
