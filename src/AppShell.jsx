import TabBar from './TabBar.jsx';

const NOISE_SVG = `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E")`;

export default function AppShell({ tabs, activeTab, onTabChange, accentColor = 'purple', title = 'CueDrop' }) {
  const activeTabDef = tabs.find((t) => t.id === activeTab) ?? tabs[0];

  return (
    <div className="flex flex-col h-screen bg-deep text-white overflow-hidden relative">
      {/* Noise texture */}
      <div
        className="fixed inset-0 pointer-events-none z-0 opacity-60"
        style={{ backgroundImage: NOISE_SVG }}
      />

      {/* Gradient orbs */}
      <div className="fixed -top-32 -left-24 w-[500px] h-[500px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(139,92,246,0.1)', filter: 'blur(100px)' }} />
      <div className="fixed -bottom-16 -right-16 w-[350px] h-[350px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(236,72,153,0.07)', filter: 'blur(100px)' }} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[250px] h-[250px] rounded-full pointer-events-none z-0"
        style={{ background: 'rgba(34,211,238,0.05)', filter: 'blur(80px)' }} />

      {/* Header */}
      <header className="relative z-10 shrink-0">
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <span
            className="text-base font-extrabold tracking-tight"
            style={{ fontFamily: 'var(--font-display)' }}
          >
            Cue<span className="text-purple-400">Drop</span>
          </span>
        </div>
        <TabBar
          tabs={tabs}
          activeTab={activeTab}
          onTabChange={onTabChange}
          accentColor={accentColor}
        />
      </header>

      {/* Content */}
      <main className="relative z-10 flex-1 overflow-hidden">
        {activeTabDef?.render(onTabChange)}
      </main>
    </div>
  );
}
