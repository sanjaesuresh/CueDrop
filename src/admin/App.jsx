import { useState, useEffect, useRef, useCallback } from 'react';
import AppShell from '../AppShell.jsx';
import HomeTab from './tabs/HomeTab.jsx';
import QueueTab from './tabs/QueueTab.jsx';
import ChatTab from './tabs/ChatTab.jsx';
import SearchTab from './tabs/SearchTab.jsx';
import SettingsTab from './tabs/SettingsTab.jsx';

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

// SVG icon helpers
const HomeIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
  </svg>
);
const QueueIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
  </svg>
);
const ChatIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
  </svg>
);
const SearchIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
const SettingsIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>
);

export default function AdminApp() {
  const [activeTab, setActiveTab] = useState('home');
  const [queueState, setQueueState] = useState({ current: null, entries: [], wildcards: [] });
  const [pendingRequests, setPendingRequests] = useState([]);

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'queue_update') setQueueState(msg.data);
  }, []);

  useAdminWebSocket(handleWsMessage);

  const refreshPending = useCallback(() => {
    fetch('/requests/pending').then(r => r.json()).then(setPendingRequests).catch(() => {});
  }, []);

  useEffect(() => {
    refreshPending();
    const interval = setInterval(refreshPending, 5000);
    return () => clearInterval(interval);
  }, [refreshPending]);

  const tabs = [
    {
      id: 'home',
      label: 'Home',
      icon: <HomeIcon />,
      render: (onTabChange) => (
        <HomeTab queueState={queueState} pendingCount={pendingRequests.length} onTabChange={onTabChange} />
      ),
    },
    {
      id: 'queue',
      label: 'Queue',
      icon: <QueueIcon />,
      render: () => <QueueTab queueState={queueState} />,
    },
    {
      id: 'chat',
      label: 'Chat',
      icon: <ChatIcon />,
      badge: pendingRequests.length,
      render: () => <ChatTab pendingRequests={pendingRequests} onRefreshRequests={refreshPending} />,
    },
    {
      id: 'search',
      label: 'Search',
      icon: <SearchIcon />,
      render: () => <SearchTab />,
    },
    {
      id: 'settings',
      label: 'Settings',
      icon: <SettingsIcon />,
      render: () => <SettingsTab />,
    },
  ];

  return (
    <AppShell
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      accentColor="purple"
    />
  );
}
