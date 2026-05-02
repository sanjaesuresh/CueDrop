const LAYER_BORDER = {
  locked:   'border-l-purple-500',
  anchor:   'border-l-purple-400',
  soft:     'border-l-purple-400/40',
  wildcard: 'border-l-amber-400',
  horizon:  'border-l-purple-500/20',
};

function UpNextEntry({ entry }) {
  const { track, layer, transition_plan } = entry;
  const border = LAYER_BORDER[layer] || 'border-l-purple-500/20';
  return (
    <div className={`rounded-xl px-3 py-2.5 bg-purple-500/[0.06] border-l-[3px] ${border}`}>
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p
            className="text-sm font-bold text-white truncate"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            {track.title}
          </p>
          <p
            className="text-[10px] text-[#4a4565] truncate mt-0.5"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            {track.artist}
            {track.bpm && <> · {track.bpm} BPM</>}
            {track.key && <> · {track.key}</>}
          </p>
        </div>
        {transition_plan?.type && (
          <span
            className="ml-2 px-2 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 shrink-0 uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.5px' }}
          >
            {transition_plan.type}
          </span>
        )}
      </div>
    </div>
  );
}

function NowPlayingCard({ current, onSearchClick }) {
  if (!current) {
    return (
      <div className="mx-3 rounded-2xl p-6 border border-purple-500/20 bg-gradient-to-br from-purple-500/10 to-pink-500/5">
        <p className="text-center text-[#4a4565] text-sm mb-3" style={{ fontFamily: 'var(--font-mono)' }}>
          No track playing
        </p>
        {onSearchClick && (
          <button
            onClick={onSearchClick}
            className="mx-auto block px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-sm font-medium transition-colors shadow-[0_0_12px_rgba(139,92,246,0.3)]"
            style={{ fontFamily: 'var(--font-display)' }}
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
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl pointer-events-none" />
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_#a78bfa] animate-pulse" />
        <span
          className="text-purple-400 uppercase"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '3px' }}
        >
          Now Playing
        </span>
      </div>
      <h2
        className="text-xl font-extrabold text-white leading-tight"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {track.title}
      </h2>
      <p
        className="text-purple-300 mt-0.5"
        style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}
      >
        {track.artist}
      </p>
      <div className="flex items-end gap-4 mt-3">
        {[
          { label: 'BPM', val: track.bpm, color: 'text-purple-500' },
          { label: 'Key', val: track.key, color: 'text-pink-500' },
          { label: 'Energy', val: track.energy, color: 'text-cyan-400' },
        ].map(({ label, val, color }) => (
          <div key={label}>
            <div
              className={`${color} uppercase`}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '1px' }}
            >
              {label}
            </div>
            <div
              className="text-lg font-bold text-white"
              style={{ fontFamily: 'var(--font-mono)' }}
            >
              {val || '—'}
            </div>
          </div>
        ))}
        {track.duration_ms && (
          <div className="ml-auto" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#4a4565' }}>
            {Math.floor(track.duration_ms / 60000)}:{String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, '0')}
          </div>
        )}
      </div>
      <div className="mt-2 h-[3px] bg-purple-500/15 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-purple-400 shadow-[0_0_6px_rgba(139,92,246,0.4)] animate-pulse"
          style={{ width: '45%' }}
        />
      </div>
    </div>
  );
}

export default function HomeTab({ queueState, pendingCount, onTabChange }) {
  const { current, entries } = queueState;
  const upNext = entries.slice(0, 2);

  const handleSkip = async () => {
    try { await fetch('/skip', { method: 'POST' }); } catch {}
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="mt-3">
        <NowPlayingCard current={current} onSearchClick={() => onTabChange('search')} />
      </div>

      <div className="flex gap-2 px-3 mt-3">
        <button
          onClick={handleSkip}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-pink-500/[0.08] border border-pink-500/15 hover:bg-pink-500/15 transition-colors active:scale-[0.97]"
        >
          <svg className="w-5 h-5 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 5v14" />
          </svg>
          <span
            className="text-pink-400 uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '1px' }}
          >
            Skip
          </span>
        </button>
        <button
          onClick={() => onTabChange('search')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-500/[0.08] border border-purple-500/15 hover:bg-purple-500/15 transition-colors active:scale-[0.97]"
        >
          <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span
            className="text-purple-400 uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '1px' }}
          >
            Search
          </span>
        </button>
        <button
          onClick={() => onTabChange('chat')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-cyan-400/[0.08] border border-cyan-400/15 hover:bg-cyan-400/15 transition-colors active:scale-[0.97] relative"
        >
          <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span
            className="text-cyan-400 uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '1px' }}
          >
            Chat
          </span>
          {pendingCount > 0 && (
            <span className="absolute top-1.5 right-[calc(50%-16px)] w-2 h-2 bg-pink-500 rounded-full shadow-[0_0_6px_#ec4899]" />
          )}
        </button>
      </div>

      <div className="px-3 mt-4 flex-1">
        <div className="flex items-center justify-between mb-2">
          <span
            className="text-[#4a4565] uppercase"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '3px' }}
          >
            Up Next
          </span>
          <button
            onClick={() => onTabChange('queue')}
            className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            View Queue →
          </button>
        </div>
        {upNext.length === 0 ? (
          <p className="text-sm text-[#4a4565] text-center py-6" style={{ fontFamily: 'var(--font-mono)' }}>
            Queue is empty
          </p>
        ) : (
          <div className="space-y-2">
            {upNext.map((entry, i) => <UpNextEntry key={i} entry={entry} />)}
          </div>
        )}
      </div>
    </div>
  );
}
