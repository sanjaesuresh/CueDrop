import { useState, useEffect, useRef, useCallback } from 'react';
import QueuePanel from './QueuePanel.jsx';
import ChatPanel from './ChatPanel.jsx';
import Settings from './Settings.jsx';
import NowPlaying from './NowPlaying.jsx';

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

export default function AdminApp() {
  const [tab, setTab] = useState('queue');
  const [showSettings, setShowSettings] = useState(false);
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
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
        <h1 className="text-lg font-bold text-emerald-400">CueDrop</h1>
        <button onClick={() => setShowSettings(true)} className="p-2 rounded-lg hover:bg-gray-700">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-hidden">
        {tab === 'queue' && <QueuePanel queueState={queueState} />}
        {tab === 'chat' && <ChatPanel pendingRequests={pendingRequests} onRefreshRequests={() => {
          fetch('/requests/pending').then(r => r.json()).then(setPendingRequests).catch(() => {});
        }} />}
      </main>

      {/* Tab Bar */}
      <nav className="flex border-t border-gray-700 bg-gray-800">
        <button
          onClick={() => setTab('queue')}
          className={`flex-1 py-3 text-sm font-medium ${tab === 'queue' ? 'text-emerald-400 border-t-2 border-emerald-400' : 'text-gray-400'}`}
        >
          Queue
        </button>
        <button
          onClick={() => setTab('chat')}
          className={`flex-1 py-3 text-sm font-medium relative ${tab === 'chat' ? 'text-emerald-400 border-t-2 border-emerald-400' : 'text-gray-400'}`}
        >
          Chat
          {pendingRequests.length > 0 && (
            <span className="absolute top-2 right-1/4 w-2 h-2 bg-red-500 rounded-full" />
          )}
        </button>
      </nav>

      {/* Settings overlay */}
      {showSettings && <Settings onClose={() => setShowSettings(false)} />}
    </div>
  );
}
