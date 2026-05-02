const LAYER_STYLES = {
  locked:   'bg-purple-500/10 border-l-[3px] border-l-purple-500',
  anchor:   'bg-purple-500/[0.07] border-l-[3px] border-l-purple-400',
  soft:     'bg-purple-500/[0.04] border-l-[3px] border-l-purple-400/40',
  wildcard: 'bg-amber-500/[0.06] border border-dashed border-amber-500/30',
  horizon:  'bg-purple-500/[0.03] border-l-[3px] border-l-purple-500/20 opacity-50',
};

const SOURCE_BADGES = {
  admin:    { label: 'Admin', cls: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  guest:    { label: 'Guest', cls: 'bg-green-500/20 text-green-400 border-green-500/30' },
  ai:       { label: 'AI',    cls: 'bg-purple-500/20 text-purple-400 border-purple-500/30' },
  wildcard: { label: 'Wild',  cls: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
};

function QueueEntry({ entry }) {
  const { track, layer, source, transition_plan } = entry;
  const layerStyle = LAYER_STYLES[layer] || 'bg-card';
  const badge = SOURCE_BADGES[source] || SOURCE_BADGES.ai;

  return (
    <div className={`px-3 py-2.5 rounded-xl ${layerStyle}`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex-1 min-w-0">
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
          </p>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {track.bpm && (
            <span className="text-purple-400" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              {track.bpm}
            </span>
          )}
          {track.key && (
            <span className="text-pink-400" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              {track.key}
            </span>
          )}
          <span
            className={`px-1.5 py-0.5 rounded border ${badge.cls}`}
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600 }}
          >
            {badge.label}
          </span>
          {transition_plan?.type && (
            <span
              className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600 }}
            >
              {transition_plan.type}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function QueueTab({ queueState }) {
  const { entries = [], wildcards = [] } = queueState;

  return (
    <div className="h-full overflow-y-auto p-3 space-y-2">
      {entries.length === 0 && wildcards.length === 0 && (
        <p
          className="text-center text-[#4a4565] text-sm py-12"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          Queue is empty
        </p>
      )}

      {entries.map((entry, i) => <QueueEntry key={`e-${i}`} entry={entry} />)}

      {wildcards.length > 0 && (
        <>
          <p
            className="text-amber-400 uppercase font-semibold mt-4 px-1"
            style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '3px' }}
          >
            Wildcards
          </p>
          {wildcards.map((entry, i) => <QueueEntry key={`w-${i}`} entry={entry} />)}
        </>
      )}
    </div>
  );
}
