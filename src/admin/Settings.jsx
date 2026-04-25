import { useState } from 'react';

const DEFAULTS = {
  session_name: 'My Set',
  guest_requests_enabled: true,
  manual_approval: true,
  cooldown_mins: 15,
  set_length_mins: 120,
  energy_arc: 'club_night',
};

export default function Settings({ onClose }) {
  const [values, setValues] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);

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
    <div className="fixed inset-0 z-50 bg-black/60" onClick={onClose}>
      <div
        className="absolute right-0 top-0 h-full w-full max-w-sm bg-gray-800 border-l border-gray-700 p-5 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-white">Settings</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>

        <div className="space-y-5">
          {/* Session name */}
          <label className="block">
            <span className="text-xs text-gray-400 uppercase">Session Name</span>
            <input
              value={values.session_name}
              onChange={(e) => update('session_name', e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-gray-700 rounded text-sm text-white outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </label>

          {/* Guest requests toggle */}
          <label className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Guest Requests</span>
            <input
              type="checkbox"
              checked={values.guest_requests_enabled}
              onChange={(e) => update('guest_requests_enabled', e.target.checked)}
              className="w-4 h-4 accent-emerald-500"
            />
          </label>

          {/* Manual approval toggle */}
          <label className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Manual Approval</span>
            <input
              type="checkbox"
              checked={values.manual_approval}
              onChange={(e) => update('manual_approval', e.target.checked)}
              className="w-4 h-4 accent-emerald-500"
            />
          </label>

          {/* Cooldown */}
          <label className="block">
            <span className="text-xs text-gray-400 uppercase">Cooldown (mins)</span>
            <input
              type="number"
              min={1}
              value={values.cooldown_mins}
              onChange={(e) => update('cooldown_mins', +e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-gray-700 rounded text-sm text-white outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </label>

          {/* Set length */}
          <label className="block">
            <span className="text-xs text-gray-400 uppercase">Set Length (mins)</span>
            <input
              type="number"
              min={10}
              value={values.set_length_mins}
              onChange={(e) => update('set_length_mins', +e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-gray-700 rounded text-sm text-white outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </label>

          {/* Energy arc */}
          <label className="block">
            <span className="text-xs text-gray-400 uppercase">Energy Arc</span>
            <select
              value={values.energy_arc}
              onChange={(e) => update('energy_arc', e.target.value)}
              className="mt-1 w-full px-3 py-2 bg-gray-700 rounded text-sm text-white outline-none focus:ring-1 focus:ring-emerald-500"
            >
              <option value="club_night">Club Night</option>
              <option value="festival">Festival</option>
              <option value="lounge">Lounge</option>
            </select>
          </label>
        </div>

        <button
          onClick={save}
          disabled={saving}
          className="mt-8 w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
