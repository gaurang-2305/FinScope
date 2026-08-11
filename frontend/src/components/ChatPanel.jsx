import { useState, useRef, useEffect } from "react";
import apiClient from "../api/client";

export default function ChatPanel({ reportId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await apiClient.post("/api/chat", {
        report_id: reportId,
        question,
      });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.data.answer,
          sources: res.data.sources || [],
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err.response?.data?.detail || "Failed to get an answer. Please try again.",
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  if (!reportId) return null;

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
        <span>Ask about this report</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask any question about the financial report.</p>
            <div className="chat-suggestions">
              {["What are the main revenue drivers?", "Summarize the risk factors", "How did operating income change?"].map((q) => (
                <button key={q} className="suggestion-btn" onClick={() => { setInput(q); }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role} ${msg.isError ? "error" : ""}`}>
            <div className="message-content">{msg.content}</div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="message-sources">
                <span className="sources-label">Sources:</span>
                {msg.sources.map((s, j) => (
                  <div key={j} className="source-chip">
                    <span className="source-idx">{j + 1}</span>
                    <span className="source-text">{s.text}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-message assistant">
            <div className="typing-indicator">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask a question..."
          className="chat-input"
          disabled={loading}
        />
        <button onClick={handleSend} disabled={!input.trim() || loading} className="chat-send">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  );
}
