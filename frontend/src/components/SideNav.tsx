import type { CSSProperties } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Tooltip } from "antd";
import { useAppStore } from "../store/appStore";
import { useConfig } from "../config";

const ALL_NAV_ITEMS: Array<{ key: string; path: string; label: string; icon: React.ReactNode }> = [
  {
    key: "agents",
    path: "/dashboard",
    label: "Dashboard",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1"/>
        <rect x="14" y="3" width="7" height="7" rx="1"/>
        <rect x="3" y="14" width="7" height="7" rx="1"/>
        <rect x="14" y="14" width="7" height="7" rx="1"/>
      </svg>
    ),
  },
  {
    key: "board",
    path: "/board",
    label: "Board",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2"/>
        <path d="M8 12h8M8 8h5M8 16h3"/>
      </svg>
    ),
  },
  {
    key: "pipeline",
    path: "/pipeline",
    label: "Pipeline",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
    ),
  },
  {
    key: "tokens",
    path: "/token-stats",
    label: "Token Stats",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 20l5-8 4 4 4-7 5 11"/>
      </svg>
    ),
  },
];

export default function SideNav() {
  const config     = useConfig();
  const navigate   = useNavigate();
  const location   = useLocation();
  const toggleChat = useAppStore((s) => s.toggleChat);
  const isChatOpen = useAppStore((s) => s.isChatOpen);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const alerts     = useAppStore((s) => s.alerts);
  const hasAlerts  = alerts.length > 0;

  const navItems = ALL_NAV_ITEMS.filter(
    (item) => item.key === "pipeline" || config.modules[item.key as keyof typeof config.modules] !== false
  );

  const navStyle: CSSProperties = {
    width: 56,
    minHeight: "100vh",
    background: "var(--nav-bg)",
    borderRight: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    paddingTop: 12,
    paddingBottom: 12,
    gap: 4,
    flexShrink: 0,
    position: "relative",
    zIndex: 10,
  };

  return (
    <nav style={navStyle}>
      {/* Logo */}
      <div style={{
        width: 34, height: 34, borderRadius: 8, marginBottom: 16, flexShrink: 0,
        background: "linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: "0 0 16px var(--accent-glow)",
      }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#000" strokeWidth="2.5" strokeLinecap="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
      </div>

      {/* Nav items */}
      {navItems.map((item) => {
        const isActive = location.pathname === item.path;
        return (
          <Tooltip key={item.path} title={item.label} placement="right">
            <div
              onClick={() => navigate(item.path)}
              style={{
                position: "relative",
                width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer",
                color: isActive ? "var(--accent)" : "var(--text-muted)",
                background: isActive ? "var(--accent-bg)" : "transparent",
                border: isActive ? "1px solid var(--accent-border)" : "1px solid transparent",
                transition: "all 0.15s",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-secondary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "var(--text-muted)";
                }
              }}
            >
              {item.icon}
              {/* Alert dot on Dashboard */}
              {item.path === "/dashboard" && hasAlerts && (
                <div style={{
                  position: "absolute", top: 6, right: 6,
                  width: 6, height: 6, borderRadius: "50%",
                  background: "#ef4444", boxShadow: "0 0 6px #ef4444",
                }}/>
              )}
            </div>
          </Tooltip>
        );
      })}

      <div style={{ flex: 1 }}/>

      {/* Chat toggle */}
      <Tooltip title="Toggle Chat" placement="right">
        <div
          onClick={toggleChat}
          style={{
            width: 40, height: 40, borderRadius: 10, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer",
            color: isChatOpen ? "var(--accent)" : "var(--text-muted)",
            background: isChatOpen ? "var(--accent-bg)" : "transparent",
            border: isChatOpen ? "1px solid var(--accent-border)" : "1px solid transparent",
            transition: "all 0.15s",
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
      </Tooltip>

      {/* WS status dot */}
      <Tooltip title={wsConnected ? "WebSocket Connected" : "Disconnected"} placement="right">
        <div style={{
          width: 8, height: 8, borderRadius: "50%", marginTop: 8, flexShrink: 0,
          background: wsConnected ? "var(--green)" : "#ef4444",
          boxShadow: wsConnected ? "0 0 8px var(--green)" : "0 0 8px #ef4444",
          animation: wsConnected ? "pulse 2s ease-in-out infinite" : "none",
        }}/>
      </Tooltip>
    </nav>
  );
}
