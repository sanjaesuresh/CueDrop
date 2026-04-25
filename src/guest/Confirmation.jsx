import { useState, useEffect } from 'react';

export default function Confirmation({ request, onRequestAnother }) {
  const [cooldownLeft, setCooldownLeft] = useState(0);

  // Cooldown timer (15 min default)
  useEffect(() => {
    if (!request) return;
    const cooldownMs = 15 * 60 * 1000;
    const submittedAt = new Date(request.submitted_at || Date.now()).getTime();
    const endTime = submittedAt + cooldownMs;

    const tick = () => {
      const remaining = Math.max(0, endTime - Date.now());
      setCooldownLeft(remaining);
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [request]);

  if (!request) return null;

  const status = request.status;
  const track = request.track;
  const cooldownActive = cooldownLeft > 0;
  const cooldownMins = Math.floor(cooldownLeft / 60000);
  const cooldownSecs = Math.floor((cooldownLeft % 60000) / 1000);

  return (
    <div className="flex flex-col items-center justify-center h-full px-6">
      {/* Track info */}
      <div className="w-20 h-20 bg-gray-800 rounded-2xl flex items-center justify-center mb-4">
        <svg className="w-10 h-10 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
          <path d="M18 3a1 1 0 00-1.196-.98l-10 2A1 1 0 006 5v9.114A4.369 4.369 0 005 14c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V7.82l8-1.6v5.894A4.37 4.37 0 0015 12c-1.657 0-3 .895-3 2s1.343 2 3 2 3-.895 3-2V3z" />
        </svg>
      </div>

      <h2 className="text-lg font-bold text-white text-center">{track?.title}</h2>
      <p className="text-sm text-gray-400 text-center">{track?.artist}</p>

      {/* Status */}
      <div className="mt-6 w-full max-w-xs">
        {status === 'pending' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-amber-900/30 border border-amber-600/30 rounded-full">
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse" />
              <span className="text-sm text-amber-300">Waiting for approval</span>
            </div>
          </div>
        )}

        {status === 'approved' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-900/30 border border-emerald-600/30 rounded-full">
              <svg className="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span className="text-sm text-emerald-300">Approved!</span>
            </div>
            {request.eta_mins && (
              <p className="text-xs text-gray-400 mt-2">
                Estimated play time: ~{Math.round(request.eta_mins)} min
              </p>
            )}
          </div>
        )}

        {status === 'declined' && (
          <div className="text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-red-900/30 border border-red-600/30 rounded-full">
              <span className="text-sm text-red-300">Request declined</span>
            </div>
            {request.decline_reason && (
              <p className="text-xs text-gray-400 mt-2">{request.decline_reason}</p>
            )}
          </div>
        )}
      </div>

      {/* Cooldown + Request Another */}
      <div className="mt-8 w-full max-w-xs">
        {cooldownActive && (
          <p className="text-center text-xs text-gray-500 mb-3">
            You can request again in {cooldownMins}:{cooldownSecs.toString().padStart(2, '0')}
          </p>
        )}
        <button
          onClick={onRequestAnother}
          disabled={cooldownActive}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-xl text-sm font-medium transition-colors"
        >
          Request Another Song
        </button>
      </div>
    </div>
  );
}
