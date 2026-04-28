import { useState, useEffect } from 'react';

export default function Confirmation({ request, onRequestAnother }) {
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

  if (!request) return null;

  const { status, track } = request;
  const cooldownActive = cooldownLeft > 0;
  const cooldownMins = Math.floor(cooldownLeft / 60000);
  const cooldownSecs = Math.floor((cooldownLeft % 60000) / 1000);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Track icon */}
      <div className="w-20 h-20 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl flex items-center justify-center mb-4 border border-purple-500/20 shadow-[0_0_20px_rgba(139,92,246,0.15)]">
        <svg className="w-10 h-10 text-purple-400" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
        </svg>
      </div>

      <h2 className="text-lg font-bold text-white text-center">{track?.title}</h2>
      <p className="text-sm text-purple-300 text-center">{track?.artist}</p>

      {/* Status */}
      <div className="mt-6 w-full max-w-xs">
        {status === 'pending' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-amber-500/10 border border-amber-500/20 rounded-full shadow-[0_0_12px_rgba(245,158,11,0.15)]">
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse shadow-[0_0_6px_#f59e0b]" />
              <span className="text-sm text-amber-300">Waiting for approval</span>
            </div>
          </div>
        )}

        {status === 'approved' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-green-500/10 border border-green-500/20 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.15)]">
              <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-green-300">Approved!</span>
            </div>
            {request.eta_mins && (
              <p className="text-xs text-slate-500 mt-2">
                Estimated play time: ~{Math.round(request.eta_mins)} min
              </p>
            )}
          </div>
        )}

        {status === 'declined' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-500/10 border border-red-500/20 rounded-full shadow-[0_0_12px_rgba(239,68,68,0.15)]">
              <span className="text-sm text-red-300">Request declined</span>
            </div>
            {request.decline_reason && (
              <p className="text-xs text-slate-500 mt-2">{request.decline_reason}</p>
            )}
          </div>
        )}
      </div>

      {/* Cooldown + Request Another */}
      <div className="mt-8 w-full max-w-xs">
        {cooldownActive && (
          <p className="text-center text-xs text-slate-600 mb-3">
            You can request again in {cooldownMins}:{cooldownSecs.toString().padStart(2, '0')}
          </p>
        )}
        <button
          onClick={onRequestAnother}
          disabled={cooldownActive}
          className="w-full py-3 bg-purple-600 hover:bg-purple-500 disabled:bg-surface disabled:text-slate-600 rounded-xl text-sm font-medium transition-colors shadow-[0_0_12px_rgba(139,92,246,0.25)] disabled:shadow-none"
        >
          Request Another Song
        </button>
      </div>
    </div>
  );
}
