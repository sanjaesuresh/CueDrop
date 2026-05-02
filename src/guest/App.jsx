import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import AppShell from '../AppShell.jsx';
import GuestSearchTab from './tabs/SearchTab.jsx';
import NowPlayingTab from './tabs/NowPlayingTab.jsx';
import MyRequestTab from './tabs/MyRequestTab.jsx';

function getDeviceId() {
  let id = sessionStorage.getItem('cuedrop_device_id');
  if (!id) { id = crypto.randomUUID(); sessionStorage.setItem('cuedrop_device_id', id); }
  return id;
}

const SearchIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
  </svg>
);
const MusicIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
  </svg>
);
const CheckIcon = () => (
  <svg fill="none" stroke="currentColor" strokeWidth="1.75" viewBox="0 0 24 24" width="18" height="18">
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

export default function GuestApp() {
  const { sessionId } = useParams();
  const [activeTab, setActiveTab] = useState('search');
  const [sessionInfo, setSessionInfo] = useState(null);
  const [submittedRequest, setSubmittedRequest] = useState(null);
  const [nowPlaying, setNowPlaying] = useState(null);
  const wsRef = useRef(null);
  const deviceId = useRef(getDeviceId());

  useEffect(() => {
    fetch(`/session/${sessionId}`)
      .then(r => r.json())
      .then((data) => { setSessionInfo(data); if (data.now_playing) setNowPlaying(data.now_playing); })
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
    ws.onmessage = (e) => { try { handleWsMessage(JSON.parse(e.data)); } catch {} };
    ws.onclose = () => {};
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
      setActiveTab('my-request');
    } catch {
      alert('Failed to submit request. Try again.');
    }
  };

  const handleRequestAnother = () => {
    setSubmittedRequest(null);
    setActiveTab('search');
  };

  const tabs = [
    {
      id: 'search',
      label: 'Search',
      icon: <SearchIcon />,
      render: () => <GuestSearchTab sessionInfo={sessionInfo} onSelect={handleSelect} />,
    },
    {
      id: 'now-playing',
      label: 'Now Playing',
      icon: <MusicIcon />,
      render: () => <NowPlayingTab nowPlaying={nowPlaying} />,
    },
    {
      id: 'my-request',
      label: 'My Request',
      icon: <CheckIcon />,
      badge: submittedRequest ? 1 : 0,
      render: () => <MyRequestTab request={submittedRequest} onRequestAnother={handleRequestAnother} />,
    },
  ];

  return (
    <AppShell
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={setActiveTab}
      accentColor="cyan"
    />
  );
}
