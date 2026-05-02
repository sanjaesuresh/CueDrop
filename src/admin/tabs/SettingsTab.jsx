import { useState, useEffect } from 'react';

const DEFAULTS = {
  session_name: 'My Set',
  guest_requests_enabled: true,
  manual_approval: true,
  cooldown_mins: 15,
  set_length_mins: 120,
  energy_arc: 'club_night',
};

const SectionLabel = ({ children }) => (
  <h3
    className="text-purple-400 uppercase font-semibold mb-3"
    style={{ fontFamily: 'var(--font-mono)', fontSize: '9px', letterSpacing: '3px' }}
  >
    {children}
  </h3>
);

const FieldLabel = ({ children }) => (
  <span className="text-[#4a4565]" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
    {children}
  </span>
);

const inputCls = 'mt-1 w-full px-3 py-2.5 bg-surface rounded-xl text-sm text-white outline-none focus:ring-2 focus:ring-purple-500/50 border border-purple-500/10';

export default function SettingsTab() {
  const [values, setValues] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [qrUrl, setQrUrl] = useState(null);
  const [sessionInfo, setSessionInfo] = useState(null);

  useEffect(() => {
    fetch('/settings').then(r => r.json()).then(data => setValues((prev) => ({ ...prev, ...data }))).catch(() => {});
    fetch('/session/qr').then(r => r.blob()).then(b => setQrUrl(URL.createObjectURL(b))).catch(() => {});
    fetch('/session/current').then(r => r.json()).then(setSessionInfo).catch(() => {});
  }, []);

  useEffect(() => {
    return () => { if (qrUrl) URL.revokeObjectURL(qrUrl); };
  }, [qrUrl]);

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

  return (
    <div className="h-full overflow-y-auto p-4 space-y-6">
      <section>
        <SectionLabel>Session</SectionLabel>
        <label className="block mb-3">
          <FieldLabel>Session Name</FieldLabel>
          <input
            value={values.session_name}
            onChange={(e) => update('session_name', e.target.value)}
            className={inputCls}
            style={{ fontFamily: 'var(--font-mono)' }}
          />
        </label>

        {qrUrl && (
          <div className="flex flex-col items-center p-4 bg-card rounded-2xl border border-purple-500/15">
            <div className="bg-white p-3 rounded-xl mb-3">
              <img src={qrUrl} alt="Session QR" className="w-36 h-36" />
            </div>
            <p className="text-[#4a4565] text-center mb-2" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
              Guests scan to request songs
            </p>
            <button
              onClick={() => {
                const a = document.createElement('a');
                a.href = qrUrl; a.download = 'cuedrop-qr.png'; a.click();
              }}
              className="w-full py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 text-sm font-medium rounded-xl border border-purple-500/20 transition-colors"
              style={{ fontFamily: 'var(--font-display)' }}
            >
              Download QR
            </button>
          </div>
        )}

        {sessionInfo && (
          <div className="mt-3 px-3 py-2 bg-card rounded-xl border border-purple-500/10">
            <div className="flex justify-between">
              <span className="text-[#4a4565]" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                Session ID
              </span>
              <span className="text-[#4a4565]" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>
                {sessionInfo.id?.slice(0, 8)}
              </span>
            </div>
          </div>
        )}
      </section>

      <section>
        <SectionLabel>Guest Requests</SectionLabel>
        {[
          { key: 'guest_requests_enabled', label: 'Requests Enabled' },
          { key: 'manual_approval', label: 'Manual Approval' },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center justify-between py-2">
            <span className="text-sm text-slate-300" style={{ fontFamily: 'var(--font-display)' }}>
              {label}
            </span>
            <input
              type="checkbox"
              checked={values[key]}
              onChange={(e) => update(key, e.target.checked)}
              className="w-4 h-4 accent-purple-500 rounded"
            />
          </label>
        ))}
        <label className="block mt-2">
          <FieldLabel>Cooldown (mins)</FieldLabel>
          <input
            type="number" min={1}
            value={values.cooldown_mins}
            onChange={(e) => update('cooldown_mins', +e.target.value)}
            className={inputCls}
            style={{ fontFamily: 'var(--font-mono)' }}
          />
        </label>
      </section>

      <section>
        <SectionLabel>Set</SectionLabel>
        <label className="block mb-3">
          <FieldLabel>Set Length (mins)</FieldLabel>
          <input
            type="number" min={10}
            value={values.set_length_mins}
            onChange={(e) => update('set_length_mins', +e.target.value)}
            className={inputCls}
            style={{ fontFamily: 'var(--font-mono)' }}
          />
        </label>
        <label className="block">
          <FieldLabel>Energy Arc</FieldLabel>
          <select
            value={values.energy_arc}
            onChange={(e) => update('energy_arc', e.target.value)}
            className={inputCls}
            style={{ fontFamily: 'var(--font-mono)' }}
          >
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
        style={{ fontFamily: 'var(--font-display)' }}
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  );
}
