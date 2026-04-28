import { useState, useEffect } from 'react';

const DEFAULTS = {
  session_name: 'My Set',
  guest_requests_enabled: true,
  manual_approval: true,
  cooldown_mins: 15,
  set_length_mins: 120,
  energy_arc: 'club_night',
};

export default function Settings() {
  const [values, setValues] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [qrUrl, setQrUrl] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);

  useEffect(() => {
    fetch('/session/qr').then(r => r.blob()).then(b => setQrUrl(URL.createObjectURL(b))).catch(() => {});
    fetch('/session/current').then(r => r.json()).then(setSessionInfo).catch(() => {});
    return () => { if (qrUrl) URL.revokeObjectURL(qrUrl); };
  }, []);

  const update = (key, val) => setValues((prev) => ({ ...prev, [key]: val }));

  const save = async () => {
    setSaving(true);
    try {
      await fetch('/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
    } catch {} finally {
      setSaving(false);
    }
  };

  const inputCls = "mt-1 w-full px-3 py-2.5 bg-surface rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-purple-500/50 border border-purple-500/10";

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Session</h3>
        <label className="block mb-3">
          <span className="text-xs text-slate-400">Session Name</span>
          <input value={values.session_name} onChange={(e) => update('session_name', e.target.value)} className={inputCls} />
        </label>

        {qrUrl && (
          <div className="flex flex-col items-center p-4 bg-card rounded-2xl border border-purple-500/15">
            <div className="bg-white p-3 rounded-xl mb-3">
              <img src={qrUrl} alt="Session QR" className="w-36 h-36" />
            </div>
            <p className="text-xs text-slate-500 text-center mb-2">Guests scan to request songs</p>
            <button
              onClick={() => {
                const a = document.createElement('a');
                a.href = qrUrl;
                a.download = 'cuedrop-qr.png';
                a.click();
              }}
              className="w-full py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-sm font-medium rounded-xl border border-purple-500/20 transition-colors"
            >
              Download QR
            </button>
          </div>
        )}

        {sessionInfo && (
          <div className="mt-3 px-3 py-2 bg-card rounded-xl border border-purple-500/10">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Session ID</span>
              <span className="text-slate-600 font-mono">{sessionInfo.id?.slice(0, 8)}</span>
            </div>
          </div>
        )}
      </section>

      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Guest Requests</h3>
        <label className="flex items-center justify-between py-2">
          <span className="text-sm text-slate-300">Requests Enabled</span>
          <input
            type="checkbox"
            checked={values.guest_requests_enabled}
            onChange={(e) => update('guest_requests_enabled', e.target.checked)}
            className="w-4 h-4 accent-purple-500 rounded"
          />
        </label>
        <label className="flex items-center justify-between py-2">
          <span className="text-sm text-slate-300">Manual Approval</span>
          <input
            type="checkbox"
            checked={values.manual_approval}
            onChange={(e) => update('manual_approval', e.target.checked)}
            className="w-4 h-4 accent-purple-500 rounded"
          />
        </label>
        <label className="block mt-2">
          <span className="text-xs text-slate-400">Cooldown (mins)</span>
          <input type="number" min={1} value={values.cooldown_mins} onChange={(e) => update('cooldown_mins', +e.target.value)} className={inputCls} />
        </label>
      </section>

      <section>
        <h3 className="text-[10px] text-purple-400 uppercase tracking-widest font-semibold mb-3">Set</h3>
        <label className="block mb-3">
          <span className="text-xs text-slate-400">Set Length (mins)</span>
          <input type="number" min={10} value={values.set_length_mins} onChange={(e) => update('set_length_mins', +e.target.value)} className={inputCls} />
        </label>
        <label className="block">
          <span className="text-xs text-slate-400">Energy Arc</span>
          <select value={values.energy_arc} onChange={(e) => update('energy_arc', e.target.value)} className={inputCls}>
            <option value="club_night">Club Night</option>
            <option value="festival">Festival</option>
            <option value="lounge">Lounge</option>
          </select>
        </label>
      </section>

      <button
        onClick={save}
        disabled={saving}
        className="w-full py-3 bg-purple-600 hover:bg-purple-500 rounded-xl text-sm font-medium disabled:opacity-40 transition-colors shadow-[0_0_12px_rgba(139,92,246,0.25)]"
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
