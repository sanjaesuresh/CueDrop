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
    <div className="bg-gray-700/50 rounded-lg p-3 border border-gray-600">
      <p className="text-xs text-amber-400 font-medium mb-1">Guest Request</p>
      <p className="text-sm font-medium">{request.track?.title}</p>
      <p className="text-xs text-gray-400">{request.track?.artist}</p>
      <div className="flex gap-2 mt-2">
        <button
          disabled={acting}
          onClick={() => handleAction('approve')}
          className="flex-1 py-1.5 text-xs font-medium rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50"
        >
          Approve
        </button>
        <button
          disabled={acting}
          onClick={() => handleAction('decline')}
          className="flex-1 py-1.5 text-xs font-medium rounded bg-red-600 hover:bg-red-500 disabled:opacity-50"
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
      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Pending approval cards */}
        {pendingRequests.map((req) => (
          <ApprovalCard key={req.id} request={req} onRefresh={onRefreshRequests} />
        ))}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] px-3 py-2 rounded-lg text-sm ${
              msg.role === 'user'
                ? 'bg-emerald-700 text-white'
                : 'bg-gray-700 text-gray-100'
            }`}>
              {msg.intent && (
                <span className="inline-block px-1.5 py-0.5 text-[10px] bg-gray-600 rounded mb-1 mr-1">
                  {msg.intent}
                </span>
              )}
              {msg.text}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex justify-start">
            <div className="bg-gray-700 text-gray-400 px-3 py-2 rounded-lg text-sm animate-pulse">
              Thinking...
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-gray-700 bg-gray-800">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Tell the AI DJ..."
            className="flex-1 px-3 py-2 bg-gray-700 rounded-lg text-sm text-white placeholder-gray-500 outline-none focus:ring-1 focus:ring-emerald-500"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="px-4 py-2 bg-emerald-600 rounded-lg text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
