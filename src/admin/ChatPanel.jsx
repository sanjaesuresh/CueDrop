import { useState, useRef, useEffect } from 'react';

function ApprovalCard({ request, onRefresh }) {
  const [acting, setActing] = useState(false);

  const handleAction = async (action) => {
    setActing(true);
    try {
      await fetch(`/${action}/${request.id}`, { method: 'POST' });
      onRefresh();
    } catch {} finally {
      setActing(false);
    }
  };

  return (
    <div className="rounded-xl p-3 bg-pink-500/[0.06] border border-pink-500/20">
      <p className="text-[10px] text-pink-400 font-semibold uppercase tracking-widest mb-1">Guest Request</p>
      <p className="text-sm font-medium text-white">{request.track?.title}</p>
      <p className="text-xs text-slate-500">{request.track?.artist}</p>
      <div className="flex gap-2 mt-2.5">
        <button
          disabled={acting}
          onClick={() => handleAction('approve')}
          className="flex-1 py-1.5 text-xs font-medium rounded-lg bg-green-500/15 text-green-400 border border-green-500/20 hover:bg-green-500/25 disabled:opacity-40 transition-colors"
        >
          Approve
        </button>
        <button
          disabled={acting}
          onClick={() => handleAction('decline')}
          className="flex-1 py-1.5 text-xs font-medium rounded-lg bg-red-500/15 text-red-400 border border-red-500/20 hover:bg-red-500/25 disabled:opacity-40 transition-colors"
        >
          Decline
        </button>
      </div>
    </div>
  );
}

export default function ChatPanel({ pendingRequests, onRefreshRequests }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight);
  }, [messages]);

  const send = async () => {
    const text = input.trim();
    if (!text || sending) return;

    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setSending(true);

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: data.response, intent: data.intent },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: 'ai', text: 'Failed to get response.' }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {pendingRequests.map((req) => (
          <ApprovalCard key={req.id} request={req} onRefresh={onRefreshRequests} />
        ))}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
              msg.role === 'user'
                ? 'bg-purple-600/40 text-white border border-purple-500/20'
                : 'bg-card text-slate-200 border border-purple-500/10'
            }`}>
              {msg.intent && (
                <span className="inline-block px-1.5 py-0.5 text-[9px] font-semibold bg-purple-500/15 text-purple-400 rounded border border-purple-500/20 mb-1 mr-1">
                  {msg.intent}
                </span>
              )}
              {msg.text}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-card text-purple-400 px-3 py-2 rounded-xl text-sm border border-purple-500/10">
              <span className="inline-flex gap-1">
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}
      </div>

      <div className="p-3 border-t border-purple-500/10 bg-deep">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Tell the AI DJ..."
            className="flex-1 px-3 py-2.5 bg-surface rounded-xl text-sm text-white placeholder-slate-500 outline-none focus:ring-2 focus:ring-purple-500/50 border border-purple-500/10"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="px-4 py-2.5 bg-purple-600 rounded-xl text-sm font-medium hover:bg-purple-500 disabled:opacity-40 transition-colors shadow-[0_0_10px_rgba(139,92,246,0.2)]"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
