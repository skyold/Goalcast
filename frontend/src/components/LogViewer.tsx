import { useEffect, useRef, useState } from "react";
import { Switch } from "antd";

export default function LogViewer() {
  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

    const connect = () => {
      wsRef.current = new WebSocket(wsUrl);
      wsRef.current.onmessage = (event) => {
        setLogs((prev) => {
          const next = [...prev, event.data as string];
          return next.length > 1000 ? next.slice(next.length - 1000) : next;
        });
      };
      wsRef.current.onclose = () => setTimeout(connect, 3000);
    };

    connect();
    return () => wsRef.current?.close();
  }, []);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const parseLevel = (line: string) => line.match(/\b(INFO|WARN|ERROR|DEBUG)\b/)?.[0] ?? "";
  const parseTime  = (line: string) => line.match(/^\[[\d:]+\]/)?.[0] ?? "";
  const parseRest  = (line: string) => line.match(/^\[\d+:\d+:\d+\]\s+\w+\s+(.*)/)?.[1] ?? line;

  const levelColor: Record<string, string> = {
    ERROR: "#ef4444",
    WARN:  "var(--accent)",
    INFO:  "var(--green)",
    DEBUG: "var(--text-muted)",
  };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--border)",
      borderRadius: "var(--radius-md)",
      overflow: "hidden",
    }}>
      {/* Terminal header */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 16px",
        borderBottom: "1px solid var(--border)",
        background: "var(--nav-bg)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", gap: 5 }}>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#ef4444" }}/>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--accent)" }}/>
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: "var(--green)" }}/>
          </div>
          <span style={{
            fontSize: 12, color: "var(--text-muted)",
            fontFamily: "var(--font-mono)", marginLeft: 6,
          }}>system.log</span>
        </div>
        <Switch
          size="small"
          checked={autoScroll}
          onChange={setAutoScroll}
          checkedChildren="Auto"
          unCheckedChildren="Manual"
        />
      </div>

      {/* Log content */}
      <div
        ref={containerRef}
        style={{
          height: 220, overflowY: "auto",
          padding: "10px 16px",
          fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.7,
          background: "#0a0a12",
        }}
      >
        {logs.length === 0 ? (
          <span style={{ color: "var(--text-muted)" }}>Waiting for logs…</span>
        ) : (
          logs.map((log, i) => {
            const lv = parseLevel(log);
            return (
              <div key={i} style={{ display: "flex", gap: 10 }}>
                <span style={{ color: "var(--text-muted)", userSelect: "none", flexShrink: 0 }}>
                  {parseTime(log)}
                </span>
                <span style={{ color: levelColor[lv] ?? "var(--text-muted)", fontWeight: 600, flexShrink: 0, minWidth: 40 }}>
                  {lv}
                </span>
                <span style={{ color: "var(--text-secondary)" }}>
                  {parseRest(log)}
                </span>
              </div>
            );
          })
        )}
        <span style={{ color: "var(--accent)", animation: "blink 1s step-end infinite" }}>▮</span>
      </div>
    </div>
  );
}
