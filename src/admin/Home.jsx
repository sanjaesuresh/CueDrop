import NowPlaying from './NowPlaying.jsx';

const LAYER_BORDER = {
  locked: 'border-l-purple-500',
  anchor: 'border-l-purple-400',
  soft: 'border-l-purple-400/40',
  wildcard: 'border-l-amber-400',
  horizon: 'border-l-purple-500/20',
};

function UpNextEntry({ entry }) {
  const { track, layer, transition_plan } = entry;
  const border = LAYER_BORDER[layer] || 'border-l-purple-500/20';

  return (
    <div className={`rounded-xl px-3 py-2.5 bg-purple-500/[0.06] border-l-[3px] ${border}`}>
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-white truncate">{track.title}</p>
          <p className="text-xs text-slate-500 truncate">
            {track.artist}
            {track.bpm && <> · {track.bpm} BPM</>}
            {track.key && <> · {track.key}</>}
          </p>
        </div>
        {transition_plan?.type && (
          <span className="ml-2 px-2 py-0.5 text-[9px] font-semibold uppercase rounded bg-purple-500/15 text-purple-400 border border-purple-500/20 shrink-0">
            {transition_plan.type}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Home({ queueState, pendingCount, onNavigate }) {
  const { current, entries } = queueState;
  const upNext = entries.slice(0, 2);

  const handleSkip = async () => {
    try { await fetch('/skip', { method: 'POST' }); } catch {}
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <header className="flex items-center justify-between px-4 py-3">
        <div>
          <p className="text-[10px] text-slate-500 uppercase tracking-widest">Session</p>
          <h1 className="text-base font-bold text-white">CueDrop</h1>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onNavigate('settings')}
            className="p-2 rounded-lg hover:bg-surface transition-colors"
            title="Settings"
          >
            <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </header>

      <div className="mt-1">
        <NowPlaying current={current} onSearchClick={() => onNavigate('search')} />
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
          <span className="text-[10px] text-pink-400 font-medium">Skip</span>
        </button>
        <button
          onClick={() => onNavigate('search')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-purple-500/[0.08] border border-purple-500/15 hover:bg-purple-500/15 transition-colors active:scale-[0.97]"
        >
          <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <span className="text-[10px] text-purple-400 font-medium">Search</span>
        </button>
        <button
          onClick={() => onNavigate('chat')}
          className="flex-1 flex flex-col items-center gap-1 py-2.5 rounded-xl bg-cyan-400/[0.08] border border-cyan-400/15 hover:bg-cyan-400/15 transition-colors active:scale-[0.97] relative"
        >
          <svg className="w-5 h-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          <span className="text-[10px] text-cyan-400 font-medium">Chat</span>
          {pendingCount > 0 && (
            <span className="absolute top-1.5 right-[calc(50%-16px)] w-2 h-2 bg-pink-500 rounded-full shadow-[0_0_6px_#ec4899]" />
          )}
        </button>
      </div>

      <div className="px-3 mt-4 flex-1">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] text-slate-500 uppercase tracking-widest">Up Next</span>
          <button
            onClick={() => onNavigate('queue')}
            className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
          >
            View Queue →
          </button>
        </div>
        {upNext.length === 0 ? (
          <p className="text-sm text-slate-600 text-center py-6">Queue is empty</p>
        ) : (
          <div className="space-y-2">
            {upNext.map((entry, i) => (
              <UpNextEntry key={i} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
