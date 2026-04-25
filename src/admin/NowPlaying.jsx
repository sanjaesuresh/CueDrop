export default function NowPlaying({ current }) {
  if (!current) {
    return (
      <div className="px-4 py-3 bg-gray-800/50 border-b border-gray-700 text-gray-500 text-sm">
        No track playing
      </div>
    );
  }

  const { track } = current;

  return (
    <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-white truncate">{track.title}</p>
          <p className="text-xs text-gray-400 truncate">{track.artist}</p>
        </div>
        <div className="flex gap-2 ml-3 shrink-0">
          {track.bpm && (
            <span className="px-2 py-0.5 text-xs rounded bg-gray-700 text-gray-300">
              {track.bpm} BPM
            </span>
          )}
          {track.key && (
            <span className="px-2 py-0.5 text-xs rounded bg-gray-700 text-gray-300">
              {track.key}
            </span>
          )}
        </div>
      </div>
      <div className="mt-2 h-1 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full bg-emerald-500 rounded-full animate-pulse" style={{ width: '45%' }} />
      </div>
    </div>
  );
}
