import NowPlaying from './NowPlaying.jsx';

const LAYER_STYLES = {
  locked: 'bg-gray-700 border-l-4 border-emerald-500',
  anchor: 'bg-emerald-900/30 border-l-4 border-emerald-400',
  soft: 'bg-gray-800/60',
  wildcard: 'bg-gray-800/40 border border-dashed border-amber-500/50',
  horizon: 'bg-gray-800/30 opacity-60',
};

const SOURCE_BADGES = {
  admin: { label: 'Admin', cls: 'bg-blue-600' },
  guest: { label: 'Guest', cls: 'bg-green-600' },
  ai: { label: 'AI', cls: 'bg-gray-600' },
};

function QueueEntry({ entry }) {
  const { track, layer, source } = entry;
  const layerStyle = LAYER_STYLES[layer] || 'bg-gray-800';
  const badge = SOURCE_BADGES[source] || SOURCE_BADGES.ai;

  return (
    <div className={`px-4 py-3 ${layerStyle} rounded-lg`}>
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-white truncate">{track.title}</p>
          <p className="text-xs text-gray-400 truncate">{track.artist}</p>
        </div>
        <div className="flex items-center gap-2 ml-2 shrink-0">
          {track.bpm && <span className="text-xs text-gray-500">{track.bpm}</span>}
          {track.key && <span className="text-xs text-gray-500">{track.key}</span>}
          <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${badge.cls} text-white`}>
            {badge.label}
          </span>
          <span className="text-[10px] text-gray-500 uppercase">{layer}</span>
        </div>
      </div>
    </div>
  );
}

export default function QueuePanel({ queueState }) {
  const { current, entries, wildcards } = queueState;

  return (
    <div className="h-full overflow-y-auto">
      <NowPlaying current={current} />

      <div className="p-3 space-y-2">
        {entries.length === 0 && wildcards.length === 0 && (
          <p className="text-center text-gray-500 text-sm py-8">Queue is empty</p>
        )}

        {entries.map((entry, i) => (
          <QueueEntry key={`e-${i}`} entry={entry} />
        ))}

        {wildcards.length > 0 && (
          <>
            <p className="text-xs text-amber-400 font-medium mt-4 px-1">Wildcards</p>
            {wildcards.map((entry, i) => (
              <QueueEntry key={`w-${i}`} entry={entry} />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
