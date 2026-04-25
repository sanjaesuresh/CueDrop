import { useState, useEffect } from 'react';

export default function SessionManager({ onClose }) {
  const [qrUrl, setQrUrl] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch('/session/qr').then((r) => r.blob()).then((b) => URL.createObjectURL(b)),
      fetch('/session/current').then((r) => r.json()).catch(() => null),
    ])
      .then(([url, info]) => {
        setQrUrl(url);
        setSessionInfo(info);
      })
      .catch(() => {})
      .finally(() => setLoading(false));

    return () => {
      if (qrUrl) URL.revokeObjectURL(qrUrl);
    };
  }, []);

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-2xl w-full max-w-sm overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <h2 className="text-lg font-bold text-white">Session</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-700 text-gray-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 flex flex-col items-center">
          {loading ? (
            <div className="text-gray-400 text-sm animate-pulse py-12">Loading...</div>
          ) : (
            <>
              {/* QR Code */}
              {qrUrl && (
                <div className="bg-white p-4 rounded-xl mb-4">
                  <img src={qrUrl} alt="Guest QR Code" className="w-48 h-48" />
                </div>
              )}

              <p className="text-sm text-gray-400 text-center mb-4">
                Guests scan this code to request songs
              </p>

              {/* Session info */}
              {sessionInfo && (
                <div className="w-full space-y-2 text-sm">
                  <div className="flex justify-between py-2 border-t border-gray-700">
                    <span className="text-gray-400">Session</span>
                    <span className="text-white font-medium">{sessionInfo.name || 'Unnamed'}</span>
                  </div>
                  {sessionInfo.genres?.length > 0 && (
                    <div className="flex justify-between py-2 border-t border-gray-700">
                      <span className="text-gray-400">Genres</span>
                      <span className="text-white">{sessionInfo.genres.join(', ')}</span>
                    </div>
                  )}
                  <div className="flex justify-between py-2 border-t border-gray-700">
                    <span className="text-gray-400">Session ID</span>
                    <span className="text-gray-500 font-mono text-xs">{sessionInfo.id?.slice(0, 8)}</span>
                  </div>
                </div>
              )}

              {/* Share button */}
              {qrUrl && (
                <button
                  onClick={() => {
                    const a = document.createElement('a');
                    a.href = qrUrl;
                    a.download = 'cuedrop-qr.png';
                    a.click();
                  }}
                  className="mt-4 w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-xl text-sm font-medium transition-colors"
                >
                  Download QR Code
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
