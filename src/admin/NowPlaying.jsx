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
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-500/10 rounded-full blur-2xl pointer-events-none" />

      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_#a78bfa] animate-pulse" />
        <span className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold">Now Playing</span>
      </div>

      <h2 className="text-xl font-extrabold text-white leading-tight">{track.title}</h2>
      <p className="text-sm text-purple-300 mt-0.5">{track.artist}</p>

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

      <div className="mt-2 h-[3px] bg-purple-500/15 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-purple-500 to-purple-400 shadow-[0_0_6px_rgba(139,92,246,0.4)] animate-pulse"
          style={{ width: '45%' }}
        />
      </div>
    </div>
  );
}
