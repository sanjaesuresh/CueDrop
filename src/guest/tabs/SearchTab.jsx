import { useState, useRef, useEffect } from 'react';

const formatDuration = (ms) => {
  if (!ms) return '';
  return `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, '0')}`;
};

export default function GuestSearchTab({ sessionInfo, onSelect }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (!query.trim()) { setResults([]); return; }
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/search?q=${encodeURIComponent(query)}&limit=10`);
        setResults(await res.json());
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  return (
    <div className="flex flex-col h-full">
      {sessionInfo && (
        <div className="px-4 pt-3 pb-1">
          <p className="text-cyan-400 font-extrabold text-base" style={{ fontFamily: 'var(--font-display)' }}>
            {sessionInfo.name || 'CueDrop'}
          </p>
        </div>
      )}

      <div className="p-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a song..."
          autoFocus
          className="w-full px-4 py-3 bg-surface rounded-xl text-white placeholder-[#4a4565] outline-none focus:ring-2 focus:ring-cyan-400/50 text-sm border border-cyan-400/10"
          style={{ fontFamily: 'var(--font-mono)' }}
        />
      </div>

      <div className="flex-1 overflow-y-auto px-3 pb-3">
        {!query.trim() && (
          <p className="text-center text-[#4a4565] text-sm mt-12" style={{ fontFamily: 'var(--font-mono)' }}>
            Search for a song to request
          </p>
        )}
        {loading && (
          <p className="text-center text-cyan-400 text-sm mt-8 animate-pulse" style={{ fontFamily: 'var(--font-mono)' }}>
            Searching...
          </p>
        )}
        {!loading && results.length > 0 && (
          <div className="space-y-1.5">
            {results.map((track) => (
              <button
                key={track.spotify_id}
                onClick={() => onSelect(track)}
                className="w-full flex items-center gap-3 p-3 bg-cyan-400/[0.04] hover:bg-cyan-400/10 rounded-xl text-left active:scale-[0.98] transition-all border border-transparent hover:border-cyan-400/15"
              >
                <div className="w-10 h-10 bg-cyan-400/10 rounded-lg flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-cyan-400" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-white truncate" style={{ fontFamily: 'var(--font-display)' }}>
                    {track.title}
                  </p>
                  <p className="text-[#4a4565] truncate" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                    {track.artist}
                  </p>
                </div>
                <span className="text-[#4a4565] shrink-0" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                  {formatDuration(track.duration_ms)}
                </span>
              </button>
            ))}
          </div>
        )}
        {!loading && query.trim() && results.length === 0 && (
          <p className="text-center text-[#4a4565] text-sm mt-8" style={{ fontFamily: 'var(--font-mono)' }}>
            No results found
          </p>
        )}
      </div>
    </div>
  );
}
