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
  const [view, setView] = useState('search'); // search | confirmation
  const [submittedRequest, setSubmittedRequest] = useState(null);
  const [nowPlaying, setNowPlaying] = useState(null);
  const wsRef = useRef(null);
  const deviceId = useRef(getDeviceId());

  // Fetch session info
  useEffect(() => {
    fetch(`/session/${sessionId}`)
      .then((r) => r.json())
      .then((data) => {
        setSessionInfo(data);
        if (data.now_playing) setNowPlaying(data.now_playing);
      })
      .catch(() => {});
  }, [sessionId]);

  // WebSocket
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

  const handleRequestAnother = () => {
    setView('search');
    setSubmittedRequest(null);
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
          <Confirmation request={submittedRequest} onRequestAnother={handleRequestAnother} />
        )}
      </main>
    </div>
  );
}
