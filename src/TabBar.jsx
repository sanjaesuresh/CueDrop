export default function TabBar({ tabs, activeTab, onTabChange, accentColor = 'purple' }) {
  const activeColor = accentColor === 'cyan'
    ? 'text-cyan-400'
    : 'text-purple-400';
  const activeBorder = accentColor === 'cyan'
    ? 'border-cyan-400 shadow-[0_2px_8px_rgba(34,211,238,0.5)]'
    : 'border-purple-400 shadow-[0_2px_8px_rgba(167,139,250,0.5)]';
  const stripBorder = accentColor === 'cyan' ? 'border-cyan-400/15' : 'border-purple-500/15';

  return (
    <div
      className={`flex overflow-x-auto scrollbar-hide border-b ${stripBorder} bg-deep/80 backdrop-blur-xl`}
      style={{ scrollbarWidth: 'none' }}
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`relative flex items-center gap-1.5 px-4 py-3 shrink-0 transition-colors ${
              isActive ? activeColor : 'text-[#4a4565] hover:text-slate-400'
            }`}
            style={{ fontFamily: 'var(--font-mono)' }}
          >
            <span className="w-[18px] h-[18px] flex items-center justify-center">
              {tab.icon}
            </span>
            <span className="text-[9px] uppercase tracking-[0.08em] whitespace-nowrap">
              {tab.label}
            </span>
            {tab.badge > 0 && (
              <span className="absolute top-2 right-2 w-[7px] h-[7px] rounded-full bg-pink-500 shadow-[0_0_6px_#ec4899]" />
            )}
            {isActive && (
              <span
                className={`absolute bottom-0 left-3 right-3 h-[2px] rounded-t border-0 ${activeBorder}`}
                style={{
                  background: accentColor === 'cyan' ? '#22d3ee' : '#a78bfa',
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
