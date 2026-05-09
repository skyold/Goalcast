import { Outlet } from "react-router-dom";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAppStore } from "../store/appStore";

export default function AppLayout() {
  useWebSocket();
  const wsConnected = useAppStore((s) => s.wsConnected);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--bg)", overflow: "hidden" }}>
      {/* Top bar */}
      <header style={{
        height: 48, flexShrink: 0,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px",
        borderBottom: "1px solid var(--border)",
        background: "var(--nav-bg)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="#00FF9D" strokeWidth="1.5" />
            <path d="M6 10l2.5 2.5L14 7" stroke="#00FF9D" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.05em" }}>
            Goalcast
          </span>
          <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 4 }}>Pipeline</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {new Date().toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })}
          </span>
          <div style={{ width: 1, height: 12, background: "var(--border)" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <div style={{
              width: 6, height: 6, borderRadius: "50%",
              background: wsConnected ? "var(--green)" : "#ef4444",
              boxShadow: wsConnected ? "0 0 5px var(--green)" : "none",
              animation: wsConnected ? "pulse 2s ease-in-out infinite" : "none",
            }} />
            <span style={{ fontSize: 11, color: wsConnected ? "var(--green)" : "#ef4444", fontFamily: "var(--font-mono)" }}>
              {wsConnected ? "Connected" : "Offline"}
            </span>
          </div>
        </div>
      </header>

      {/* Page content */}
      <main style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        <Outlet />
      </main>
    </div>
  );
}
