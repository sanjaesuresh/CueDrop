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
      {/* Search input */}
      <div className="p-4">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a song..."
          autoFocus
          className="w-full px-4 py-3 bg-gray-800 rounded-xl text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-emerald-500 text-base"
        />
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {!query.trim() && (
          <p className="text-center text-gray-500 text-sm mt-12">
            Search for a song to request
          </p>
        )}

        {loading && (
          <div className="text-center text-gray-400 text-sm mt-8 animate-pulse">
            Searching...
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="space-y-2">
            {results.map((track) => (
              <button
                key={track.spotify_id}
                onClick={() => onSelect(track)}
                className="w-full flex items-center gap-3 p-3 bg-gray-800/60 hover:bg-gray-700 rounded-xl text-left active:scale-[0.98] transition-transform"
              >
                <div className="w-10 h-10 bg-gray-700 rounded-lg flex items-center justify-center shrink-0">
                  <svg className="w-5 h-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{track.title}</p>
                  <p className="text-xs text-gray-400 truncate">{track.artist}</p>
                </div>
                <span className="text-xs text-gray-500 shrink-0">
                  {formatDuration(track.duration_ms)}
                </span>
              </button>
            ))}
          </div>
        )}

        {!loading && query.trim() && results.length === 0 && (
          <p className="text-center text-gray-500 text-sm mt-8">No results found</p>
        )}
      </div>
    </div>
  );
}
