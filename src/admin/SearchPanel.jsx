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
      {toast && (
        <div className="absolute top-2 left-4 right-4 z-10 px-4 py-2 bg-purple-600/90 backdrop-blur rounded-xl text-sm text-white text-center shadow-[0_0_15px_rgba(139,92,246,0.3)] animate-pulse">
          {toast}
        </div>
      )}

      <div className="p-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Spotify..."
          autoFocus
          className="w-full px-4 py-3 bg-surface rounded-xl text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-purple-500/50 text-sm border border-purple-500/10"
        />
      </div>

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
