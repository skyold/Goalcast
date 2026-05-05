import { Outlet, useLocation } from "react-router-dom";
import SideNav from "../components/SideNav";
import ChatPanel from "../pages/ChatPanel";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAppStore } from "../store/appStore";

export default function AppLayout() {
  useWebSocket();
  const location = useLocation();

  const wsConnected = useAppStore((s) => s.wsConnected);
  const isChatOpen  = useAppStore((s) => s.isChatOpen);

  return (
    <div style={{ display: "flex", height: "100vh", background: "var(--bg)", overflow: "hidden" }}>
      <SideNav />

      {/* Main area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* Top bar */}
        <header style={{
          height: 48,
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "0 22px",
          borderBottom: "1px solid var(--border)",
          background: "var(--nav-bg)",
          flexShrink: 0,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--accent)", letterSpacing: "0.08em" }}>
              Goalcast
            </span>
            <span style={{ color: "var(--border)", fontSize: 12 }}>|</span>
            <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
              Orchestrator
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </span>
            {/* WS indicator */}
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <div style={{
                width: 6, height: 6, borderRadius: "50%",
                background: wsConnected ? "var(--green)" : "#ef4444",
                boxShadow: wsConnected ? "0 0 6px var(--green)" : "0 0 6px #ef4444",
                animation: wsConnected ? "pulse 2s ease-in-out infinite" : "none",
              }}/>
              <span style={{
                fontSize: 11,
                color: wsConnected ? "var(--green)" : "#ef4444",
                fontFamily: "var(--font-mono)",
              }}>
                {wsConnected ? "Connected" : "Disconnected"}
              </span>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, overflowY: "auto", padding: 22 }}>
          <div className="page-enter" key={location.pathname}>
            <Outlet />
          </div>
        </main>
      </div>

      {isChatOpen && <ChatPanel />}
    </div>
  );
}
