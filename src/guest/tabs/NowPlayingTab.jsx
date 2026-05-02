const WAVE_HEIGHTS = [8, 14, 10, 16, 6];

export default function NowPlayingTab({ nowPlaying }) {
  const track = nowPlaying?.track ?? null;

  if (!track) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <p className="text-[#4a4565] text-sm" style={{ fontFamily: 'var(--font-mono)' }}>
          No track playing yet
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Waveform */}
      <div className="flex items-end gap-[3px] h-8 mb-8">
        {WAVE_HEIGHTS.map((h, i) => (
          <span
            key={i}
            className="w-[4px] rounded-sm bg-cyan-400 opacity-60"
            style={{
              height: `${h * 1.5}px`,
              animation: `wave 1s ease-in-out ${i * 0.15}s infinite`,
            }}
          />
        ))}
      </div>

      {/* Live label */}
      <div className="flex items-center gap-2 mb-4">
        <span
          className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"
          style={{ boxShadow: '0 0 8px #22d3ee' }}
        />
        <span
          className="text-cyan-400 uppercase"
          style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '3px' }}
        >
          Now Playing
        </span>
      </div>

      {/* Track info */}
      <h2
        className="text-2xl font-extrabold text-white text-center leading-tight"
        style={{ fontFamily: 'var(--font-display)', letterSpacing: '-0.5px' }}
      >
        {track.title}
      </h2>
      <p
        className="text-purple-300 mt-1 text-center"
        style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}
      >
        {track.artist}
      </p>

      {/* Stats strip */}
      <div
        className="flex mt-6 border border-cyan-400/18 rounded-xl overflow-hidden"
        style={{ background: 'var(--color-card)' }}
      >
        {[
          { label: 'BPM',    val: track.bpm,    color: 'text-purple-400' },
          { label: 'Key',    val: track.key,    color: 'text-pink-400' },
          { label: 'Energy', val: track.energy, color: 'text-cyan-400' },
        ].map(({ label, val, color }, i, arr) => (
          <div
            key={label}
            className={`px-5 py-3 text-center ${i < arr.length - 1 ? 'border-r border-cyan-400/15' : ''}`}
          >
            <span
              className={`block font-bold ${color}`}
              style={{ fontFamily: 'var(--font-mono)', fontSize: '16px' }}
            >
              {val || '—'}
            </span>
            <span
              className="block text-[#4a4565] mt-0.5 uppercase tracking-wider"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}
            >
              {label}
            </span>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes wave {
          0%, 100% { transform: scaleY(1); }
          50% { transform: scaleY(0.25); }
        }
      `}</style>
    </div>
  );
}
