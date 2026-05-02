import { useNavigate } from 'react-router-dom';

const NOISE_SVG = `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E")`;

const CHIPS = [
  { label: 'Harmonic mixing', color: 'purple' },
  { label: 'Energy-aware AI', color: 'pink' },
  { label: 'Guest QR requests', color: 'cyan' },
  { label: '5-layer queue', color: 'purple' },
  { label: 'VirtualDJ control', color: 'pink' },
  { label: 'Learning graph', color: 'cyan' },
];

const CHIP_STYLES = {
  purple: 'text-purple-400 border-purple-500/25 bg-purple-500/8',
  pink:   'text-pink-400   border-pink-500/25   bg-pink-500/8',
  cyan:   'text-cyan-400   border-cyan-400/25   bg-cyan-400/8',
};

const WAVE_HEIGHTS = [8, 14, 10, 16, 6];

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen bg-[#07050f] text-white overflow-x-hidden"
      style={{ fontFamily: 'var(--font-display)' }}
    >
      {/* Noise */}
      <div className="fixed inset-0 pointer-events-none z-0 opacity-60"
        style={{ backgroundImage: NOISE_SVG }} />
      {/* Orbs */}
      <div className="fixed -top-40 -left-32 w-[600px] h-[600px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(139,92,246,0.1)', filter: 'blur(100px)' }} />
      <div className="fixed bottom-0 -right-24 w-[400px] h-[400px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(236,72,153,0.07)', filter: 'blur(100px)' }} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[300px] h-[300px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(34,211,238,0.05)', filter: 'blur(80px)' }} />

      <div className="relative z-10 max-w-[1200px] mx-auto px-6 md:px-12 lg:px-16">

        {/* Nav */}
        <nav className="flex items-center justify-between pt-6 md:pt-8">
          <span className="text-[20px] font-extrabold tracking-tight">
            Cue<span className="text-purple-400">Drop</span>
          </span>
          <div className="flex items-center gap-4">
            <span
              className="text-[9px] text-[#4a4565] border border-purple-500/15 px-2.5 py-1 rounded"
              style={{ fontFamily: 'var(--font-mono)', letterSpacing: '1px' }}
            >
              v2.0 · BETA
            </span>
            <button
              onClick={() => navigate('/admin')}
              className="hidden md:block text-[10px] text-purple-400 border border-purple-500/35 bg-purple-500/15 px-4 py-2 rounded-lg hover:bg-purple-500/25 transition-colors"
              style={{ fontFamily: 'var(--font-mono)', letterSpacing: '1px', textTransform: 'uppercase' }}
            >
              Open Admin →
            </button>
          </div>
        </nav>

        {/* Hero grid */}
        <div className="mt-12 md:mt-16 flex flex-col md:flex-row md:items-start md:gap-16 lg:gap-20">

          {/* Left: hero text */}
          <div className="flex-[1.1]">
            <p
              className="flex items-center gap-2 text-purple-400 mb-4"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '10px', letterSpacing: '3px', textTransform: 'uppercase' }}
            >
              <span className="w-6 h-px bg-purple-400 inline-block" />
              AI-Powered DJ Assistant
            </p>

            <h1
              className="font-extrabold leading-[0.92] tracking-[-3px] text-white"
              style={{ fontSize: 'clamp(44px, 12vw, 88px)', fontFamily: 'var(--font-display)' }}
            >
              The set<br />
              <span style={{
                background: 'linear-gradient(110deg, #a78bfa 0%, #ec4899 55%, #22d3ee 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}>
                never stops.
              </span>
            </h1>

            <p
              className="text-[#4a4565] mt-5 max-w-[340px] leading-[1.8]"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}
            >
              Autonomous track selection · harmonic transitions · real-time guest requests via QR code. Powered by Claude.
            </p>

            <div className="flex flex-wrap gap-1.5 mt-6">
              {CHIPS.map((chip) => (
                <span
                  key={chip.label}
                  className={`border rounded px-2.5 py-[5px] ${CHIP_STYLES[chip.color]}`}
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '0.5px' }}
                >
                  {chip.label}
                </span>
              ))}
            </div>
          </div>

          {/* Right: role cards */}
          <div className="flex-[0.9] mt-10 md:mt-2">
            <p
              className="text-[#4a4565] mb-3"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '3px', textTransform: 'uppercase' }}
            >
              — Choose your role
            </p>

            {/* DJ card */}
            <button
              onClick={() => navigate('/admin')}
              className="w-full flex items-center justify-between rounded-[18px] px-6 py-5 mb-2.5 text-left transition-transform hover:-translate-y-0.5 active:scale-[0.985]"
              style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.22) 0%, rgba(139,92,246,0.06) 100%)',
                border: '1px solid rgba(139,92,246,0.35)',
                boxShadow: '0 0 40px rgba(139,92,246,0.08)',
              }}
            >
              <div>
                <p
                  className="text-purple-400 mb-1"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '2px', textTransform: 'uppercase' }}
                >
                  DJ · Admin
                </p>
                <h2
                  className="text-white font-extrabold leading-tight tracking-tight"
                  style={{ fontFamily: 'var(--font-display)', fontSize: '22px' }}
                >
                  I'm running<br />the set.
                </h2>
                <p
                  className="text-[#4a4565] mt-1"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}
                >
                  Dashboard · Queue · Chat · Settings
                </p>
              </div>
              <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 ml-4 text-purple-400"
                style={{ background: 'rgba(139,92,246,0.25)', border: '1px solid rgba(139,92,246,0.4)' }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </button>

            {/* Guest card */}
            <button
              onClick={() => navigate('/guest/join')}
              className="w-full flex items-center justify-between rounded-[18px] px-6 py-5 text-left transition-transform hover:-translate-y-0.5 active:scale-[0.985]"
              style={{
                background: 'linear-gradient(135deg, rgba(34,211,238,0.12) 0%, rgba(34,211,238,0.03) 100%)',
                border: '1px solid rgba(34,211,238,0.25)',
                boxShadow: '0 0 40px rgba(34,211,238,0.05)',
              }}
            >
              <div>
                <p
                  className="text-cyan-400 mb-1"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '2px', textTransform: 'uppercase' }}
                >
                  Guest · Listener
                </p>
                <h2
                  className="text-white font-extrabold leading-tight tracking-tight"
                  style={{ fontFamily: 'var(--font-display)', fontSize: '22px' }}
                >
                  I want to<br />request a song.
                </h2>
                <p
                  className="text-[#4a4565] mt-1"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}
                >
                  Search Spotify · Submit · Track status
                </p>
              </div>
              <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 ml-4 text-cyan-400"
                style={{ background: 'rgba(34,211,238,0.15)', border: '1px solid rgba(34,211,238,0.3)' }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                  <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
            </button>
          </div>
        </div>

        {/* Bottom strip */}
        <div className="mt-10 mb-12 flex flex-col md:flex-row gap-3">
          {/* Stats */}
          <div
            className="flex border border-purple-500/18 rounded-xl overflow-hidden md:flex-1"
            style={{ background: 'var(--color-card)' }}
          >
            {[
              { val: '5', label: 'Queue layers', color: 'text-purple-400' },
              { val: 'Neo4j', label: 'Graph DB', color: 'text-pink-400' },
              { val: 'Claude', label: 'AI NLU', color: 'text-cyan-400' },
              { val: '128', label: 'BPM sync', color: 'text-purple-400' },
            ].map((stat, i, arr) => (
              <div
                key={stat.label}
                className={`flex-1 px-3 py-3 text-center ${i < arr.length - 1 ? 'border-r border-purple-500/18' : ''}`}
              >
                <span
                  className={`block font-bold ${stat.color}`}
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '14px' }}
                >
                  {stat.val}
                </span>
                <span
                  className="block text-[#4a4565] mt-0.5 uppercase tracking-wider"
                  style={{ fontFamily: 'var(--font-mono)', fontSize: '8px' }}
                >
                  {stat.label}
                </span>
              </div>
            ))}
          </div>

          {/* Live bar */}
          <div
            className="relative flex items-center gap-3 rounded-xl px-4 py-3 overflow-hidden md:flex-[1.4]"
            style={{ background: 'var(--color-card)', border: '1px solid rgba(139,92,246,0.18)' }}
          >
            <div className="absolute top-0 left-0 w-[3px] h-full bg-purple-400 rounded-r"
              style={{ boxShadow: '0 0 8px #a78bfa' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-purple-400 shrink-0 animate-pulse"
              style={{ boxShadow: '0 0 8px #a78bfa' }} />
            <span
              className="flex-1 text-[#4a4565]"
              style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}
            >
              <strong className="text-purple-400">Live session</strong> · Now playing: Bicep — Glue (Original Mix)
            </span>
            <div className="flex items-end gap-[3px] h-4">
              {WAVE_HEIGHTS.map((h, i) => (
                <span
                  key={i}
                  className="w-[3px] rounded-sm bg-purple-400 opacity-50"
                  style={{
                    height: `${h}px`,
                    animation: `wave 1s ease-in-out ${i * 0.15}s infinite`,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
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
