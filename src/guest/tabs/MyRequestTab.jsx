import { useState, useEffect } from 'react';

const STATUS_STYLES = {
  pending: {
    wrap: 'bg-amber-500/10 border-amber-500/20 shadow-[0_0_12px_rgba(245,158,11,0.15)]',
    dot:  'bg-amber-400 shadow-[0_0_6px_#f59e0b] animate-pulse',
    text: 'text-amber-300',
    label: 'Waiting for approval',
  },
  approved: {
    wrap: 'bg-green-500/10 border-green-500/20 shadow-[0_0_12px_rgba(34,197,94,0.15)]',
    dot:  null,
    text: 'text-green-300',
    label: 'Approved!',
  },
  declined: {
    wrap: 'bg-red-500/10 border-red-500/20 shadow-[0_0_12px_rgba(239,68,68,0.15)]',
    dot:  null,
    text: 'text-red-300',
    label: 'Request declined',
  },
};

export default function MyRequestTab({ request, onRequestAnother }) {
  const [cooldownLeft, setCooldownLeft] = useState(0);

  useEffect(() => {
    if (!request) return;
    const cooldownMs = 15 * 60 * 1000;
    const submittedAt = new Date(request.submitted_at || Date.now()).getTime();
    const endTime = submittedAt + cooldownMs;
    const tick = () => setCooldownLeft(Math.max(0, endTime - Date.now()));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [request]);

  if (!request) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-6">
        <p className="text-[#4a4565] text-sm text-center" style={{ fontFamily: 'var(--font-mono)' }}>
          Submit a request from the Search tab
        </p>
      </div>
    );
  }

  const { status, track } = request;
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  const cooldownActive = cooldownLeft > 0;
  const cooldownMins = Math.floor(cooldownLeft / 60000);
  const cooldownSecs = String(Math.floor((cooldownLeft % 60000) / 1000)).padStart(2, '0');

  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Track icon */}
      <div
        className="w-20 h-20 rounded-2xl flex items-center justify-center mb-4 border border-purple-500/20"
        style={{
          background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(236,72,153,0.2))',
          boxShadow: '0 0 20px rgba(139,92,246,0.15)',
        }}
      >
        <svg className="w-10 h-10 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
        </svg>
      </div>

      <h2
        className="text-lg font-extrabold text-white text-center"
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {track?.title}
      </h2>
      <p className="text-purple-300 text-center mt-0.5" style={{ fontFamily: 'var(--font-mono)', fontSize: '11px' }}>
        {track?.artist}
      </p>

      {/* Status pill */}
      <div className="mt-6 w-full max-w-xs">
        <div className="text-center">
          <div className={`inline-flex items-center gap-2 px-5 py-2.5 border rounded-full ${style.wrap}`}>
            {style.dot && <span className={`w-2 h-2 rounded-full ${style.dot}`} />}
            {status === 'approved' && (
              <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            )}
            <span className={`text-sm ${style.text}`} style={{ fontFamily: 'var(--font-display)' }}>
              {style.label}
            </span>
          </div>
          {status === 'approved' && request.eta_mins && (
            <p className="text-[#4a4565] mt-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              Estimated play time: ~{Math.round(request.eta_mins)} min
            </p>
          )}
          {status === 'declined' && request.decline_reason && (
            <p className="text-[#4a4565] mt-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              {request.decline_reason}
            </p>
          )}
        </div>
      </div>

      {/* Cooldown + button */}
      <div className="mt-8 w-full max-w-xs">
        {cooldownActive && (
          <p className="text-center text-[#4a4565] mb-3" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
            You can request again in {cooldownMins}:{cooldownSecs}
          </p>
        )}
        <button
          onClick={onRequestAnother}
          disabled={cooldownActive}
          className="w-full py-3 rounded-xl text-sm font-medium transition-colors"
          style={{
            fontFamily: 'var(--font-display)',
            background: cooldownActive ? 'var(--color-surface)' : 'linear-gradient(135deg, rgba(34,211,238,0.8), rgba(34,211,238,0.6))',
            color: cooldownActive ? '#4a4565' : '#07050f',
            cursor: cooldownActive ? 'not-allowed' : 'pointer',
            boxShadow: cooldownActive ? 'none' : '0 0 16px rgba(34,211,238,0.25)',
          }}
        >
          Request Another Song
        </button>
      </div>
    </div>
  );
}
