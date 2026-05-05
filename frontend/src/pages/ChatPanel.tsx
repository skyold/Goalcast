import { useState, useRef, useEffect, useCallback } from "react";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { ChatMessage } from "../types";

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content: "Hi! I'm the FAFETS console assistant.\n\nTry:\n• Check agent status\n• List recent factors\n• Start / stop pipelines\n• Show token stats",
  timestamp: "",
};

const QUICK_PROMPTS = ["Agent status", "Show factors", "Token cost"];

export default function ChatPanel() {
  const chatMessages  = useAppStore((s) => s.chatMessages);
  const addChatMessage = useAppStore((s) => s.addChatMessage);
  const toggleChat    = useAppStore((s) => s.toggleChat);
  const pendingChatInjection = useAppStore((s) => s.pendingChatInjection);
  const clearChatInjection = useAppStore((s) => s.clearChatInjection);

  const [input, setInput]     = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingAutoSend, setPendingAutoSend] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.parentElement!.scrollTop = bottomRef.current.offsetTop;
    }
  }, [chatMessages, loading]);

  // Consume injected message: fill input and trigger auto-send
  useEffect(() => {
    if (!pendingChatInjection) return;
    setInput(pendingChatInjection);
    setPendingAutoSend(true);
    clearChatInjection();
  }, [pendingChatInjection, clearChatInjection]);

  const displayMessages = chatMessages.length > 0 ? chatMessages : [WELCOME_MESSAGE];

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    addChatMessage(userMsg);
    setInput("");
    setLoading(true);

    try {
      const history = chatMessages
        .slice(-20)
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await api.sendChat({ message: text, history });
      addChatMessage({
        ...res,
        id: res.id || `assistant-${Date.now()}`,
        timestamp: new Date().toISOString(),
      });
    } catch (e) {
      addChatMessage({
        id: `err-${Date.now()}`,
        role: "system",
        content: `Error: ${String(e)}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  }, [input, loading, chatMessages, addChatMessage]);

  // Wait for input state to update, then auto-send (skip if a prior send is in-flight)
  useEffect(() => {
    if (pendingAutoSend && input && !loading) {
      handleSend();
      setPendingAutoSend(false);
    }
  }, [pendingAutoSend, input, loading, handleSend]);

  return (
    <div style={{
      width: 280, flexShrink: 0,
      background: "var(--nav-bg)",
      borderLeft: "1px solid var(--border)",
      display: "flex", flexDirection: "column",
      height: "100vh", position: "sticky", top: 0,
    }}>
      {/* Header */}
      <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--accent-bg)", border: "1px solid var(--accent-border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>Assistant</div>
            <div style={{ fontSize: 10, color: "var(--green)", display: "flex", alignItems: "center", gap: 4 }}>
              <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--green)", display: "inline-block" }}/>
              Online
            </div>
          </div>
        </div>
        <button
          onClick={toggleChat}
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 18, lineHeight: 1, padding: "2px 4px", borderRadius: 4 }}
          onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = "var(--text-primary)")}
          onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = "var(--text-muted)")}
        >×</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 10px", display: "flex", flexDirection: "column", gap: 8 }}>
        {displayMessages.map((msg) => {
          const isUser = msg.role === "user";
          const isSys  = msg.role === "system";
          return (
            <div key={msg.id} style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
              {!isUser && !isSys && (
                <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 3, marginLeft: 4 }}>Assistant</div>
              )}
              <div style={{
                maxWidth: "88%", padding: "8px 11px",
                borderRadius: isUser ? "12px 12px 3px 12px" : isSys ? 8 : "12px 12px 12px 3px",
                fontSize: 12.5, lineHeight: 1.55, whiteSpace: "pre-wrap",
                background: isUser ? "var(--accent-bg)" : isSys ? "rgba(239,68,68,0.08)" : "var(--card-bg)",
                color:      isUser ? "var(--accent)"    : isSys ? "#ef4444"                : "var(--text-secondary)",
                border:     isUser ? "1px solid var(--accent-border)" : isSys ? "1px solid rgba(239,68,68,0.2)" : "1px solid var(--border)",
              }}>
                {msg.content}
              </div>
              {msg.timestamp && (
                <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3, [isUser ? "marginRight" : "marginLeft"]: 4 }}>
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </div>
              )}
            </div>
          );
        })}

        {/* Typing indicator */}
        {loading && (
          <div style={{ alignSelf: "flex-start", padding: "8px 12px", borderRadius: "12px 12px 12px 3px", background: "var(--card-bg)", border: "1px solid var(--border)" }}>
            <div style={{ display: "flex", gap: 4, alignItems: "center", height: 16 }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent)", animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }}/>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef}/>
      </div>

      {/* Quick prompts */}
      <div style={{ padding: "6px 10px", borderTop: "1px solid var(--border)", display: "flex", gap: 5, flexWrap: "wrap", flexShrink: 0 }}>
        {QUICK_PROMPTS.map((q) => (
          <button
            key={q}
            onClick={() => { setInput(q); setTimeout(() => inputRef.current?.focus(), 0); }}
            style={{ padding: "3px 9px", borderRadius: 20, fontSize: 11, cursor: "pointer", background: "var(--hover-bg)", border: "1px solid var(--border)", color: "var(--text-muted)", fontFamily: "inherit", transition: "all 0.15s" }}
            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--accent-border)"; (e.currentTarget as HTMLElement).style.color = "var(--accent)"; }}
            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";        (e.currentTarget as HTMLElement).style.color = "var(--text-muted)"; }}
          >{q}</button>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding: "8px 10px", borderTop: "1px solid var(--border)", display: "flex", gap: 6, alignItems: "flex-end", flexShrink: 0 }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }}}
          placeholder="Ask anything… (Enter to send)"
          rows={1}
          style={{
            flex: 1, padding: "8px 10px", borderRadius: 8,
            border: "1px solid var(--border)", background: "var(--card-bg)",
            color: "var(--text-primary)", fontSize: 12.5, fontFamily: "inherit",
            resize: "none", outline: "none", lineHeight: 1.5, maxHeight: 80, overflowY: "auto",
            transition: "border-color 0.15s",
          }}
          onFocus={(e) => (e.target.style.borderColor = "var(--accent)")}
          onBlur={(e)  => (e.target.style.borderColor = "var(--border)")}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            width: 34, height: 34, borderRadius: 8, border: "none", cursor: "pointer",
            background: input.trim() ? "var(--accent)" : "var(--hover-bg)",
            color:      input.trim() ? "#000"          : "var(--text-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.15s", flexShrink: 0,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <line x1="22" y1="2" x2="11" y2="13"/>
            <polygon points="22 2 15 22 11 13 2 9 22 2" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </div>
  );
}
