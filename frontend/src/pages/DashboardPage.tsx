import { useEffect, useState } from "react";
import { Tooltip } from "antd";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import { useConfig } from "../config";
import type { AgentStatus } from "../types";
import LogViewer from "../components/LogViewer";
import AgentDetailDrawer from "../components/AgentDetailDrawer";
import DashboardExtras from "../extensions/DashboardExtras";

// ── Helpers ────────────────────────────────────────────────────────────

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

// ── Status Badge ───────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; bg: string; label: string }> = {
    running: { color: "var(--green)",      bg: "rgba(74,222,128,0.1)",  label: "Running" },
    idle:    { color: "var(--text-muted)", bg: "var(--hover-bg)",       label: "Idle"    },
    error:   { color: "#ef4444",           bg: "rgba(239,68,68,0.1)",   label: "Error"   },
    warning: { color: "var(--accent)",     bg: "var(--accent-bg)",      label: "Warning" },
  };
  const s = map[status] ?? map.idle;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      padding: "2px 8px", borderRadius: 20,
      fontSize: 11, fontWeight: 600,
      color: s.color, background: s.bg,
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: "50%", background: s.color, display: "inline-block",
        boxShadow: status === "running" ? `0 0 6px ${s.color}` : "none",
      }}/>
      {s.label}
    </span>
  );
}

// ── Stat Card ──────────────────────────────────────────────────────────

function StatCard({
  label, value, color, detail, onClick,
}: {
  label: string; value: string | number; color: string; detail?: string; onClick?: () => void;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        background: "var(--card-bg)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)", padding: "14px 16px",
        cursor: onClick ? "pointer" : "default",
        transition: "border-color 0.15s", position: "relative", overflow: "hidden",
      }}
      onMouseEnter={(e) => onClick && ((e.currentTarget as HTMLElement).style.borderColor = "var(--accent-border)")}
      onMouseLeave={(e) => onClick && ((e.currentTarget as HTMLElement).style.borderColor = "var(--border)")}
    >
      <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600, marginBottom: 6 }}>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 700, color, lineHeight: 1, letterSpacing: "-0.02em" }}>
        {value}
      </div>
      {detail && (
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {detail}
        </div>
      )}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, ${color} 0%, transparent 100%)`,
        opacity: 0.4,
      }}/>
    </div>
  );
}

// ── Agent Unified Panel ────────────────────────────────────────────────

function AgentUnifiedPanel({
  agents,
  onSelectAgent,
}: {
  agents: AgentStatus[];
  onSelectAgent: (id: string) => void;
}) {
  const config = useConfig();

  return (
    <div style={{ background: "var(--card-bg)", border: "1px solid var(--border)", borderRadius: "var(--radius-md)", overflow: "hidden" }}>
      {/* Header row */}
      <div style={{ padding: "7px 16px", borderBottom: "1px solid var(--border-subtle)", display: "flex", justifyContent: "space-between" }}>
        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>All Agents</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {agents.length} agents
        </span>
      </div>

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "var(--nav-bg)" }}>
              {["Cluster", "Agent ID", "Role", "Status", "Current Task", "Last Active"].map((h) => (
                <th key={h} style={{ padding: "8px 16px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
                  No agents available
                </td>
              </tr>
            ) : (
              agents.map((agent, i, arr) => {
                const clusterDef = config.agents.clusters.find((c) => c.key === agent.cluster);
                return (
                  <tr
                    key={agent.agent_id}
                    style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border-subtle)" : "none" }}
                    onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--hover-bg)")}
                    onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
                  >
                    <td style={{ padding: "10px 16px" }}>
                      <span style={{
                        color: clusterDef?.color ?? "var(--text-muted)", fontSize: 11, fontWeight: 600,
                      }}>
                        {clusterDef?.label ?? agent.cluster}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                      <span
                        onClick={() => onSelectAgent(agent.agent_id)}
                        style={{ color: "var(--accent)", cursor: "pointer", borderBottom: "1px dashed var(--accent-border)" }}
                      >
                        {agent.agent_id}
                      </span>
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>{agent.role}</td>
                    <td style={{ padding: "10px 16px" }}><StatusBadge status={agent.status}/></td>
                    <td style={{ padding: "10px 16px", color: "var(--text-muted)", maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {agent.task || "—"}
                    </td>
                    <td style={{ padding: "10px 16px", color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 11, whiteSpace: "nowrap" }}>
                      {agent.last_active || "—"}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Alert Bar ──────────────────────────────────────────────────────────

function AlertBar() {
  const alerts = useAppStore((s) => s.alerts);
  const dismissAlert = useAppStore((s) => s.dismissAlert);
  if (!alerts.length) return null;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {alerts.map((alert, i) => (
        <div key={i} style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "9px 14px", borderRadius: 10, fontSize: 13,
          background: alert.level === "error" ? "rgba(239,68,68,0.08)" : "rgba(255,149,0,0.08)",
          border: `1px solid ${alert.level === "error" ? "rgba(239,68,68,0.25)" : "rgba(255,149,0,0.25)"}`,
        }}>
          <span>{alert.level === "error" ? "⛔" : "⚠️"}</span>
          <span style={{ color: alert.level === "error" ? "#ef4444" : "var(--accent)", fontWeight: 600, flexShrink: 0 }}>
            {alert.agent_id}
          </span>
          <span style={{ color: "var(--text-secondary)", flex: 1 }}>{alert.message}</span>
          <span style={{ color: "var(--text-muted)", fontSize: 11, flexShrink: 0 }}>{alert.timestamp}</span>
          <button
            onClick={() => dismissAlert(alert.agent_id)}
            style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 16, lineHeight: 1, padding: "0 4px" }}
          >×</button>
        </div>
      ))}
    </div>
  );
}

// ── Dashboard Page ─────────────────────────────────────────────────────

export default function DashboardPage() {
  const config       = useConfig();
  const agentMap     = useAppStore((s) => s.agents);
  const wsConnected  = useAppStore((s) => s.wsConnected);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [tokenSummary, setTokenSummary] = useState<{ total_tokens: number; total_cost: number } | null>(null);
  const agents = Object.values(agentMap);

  useEffect(() => {
    api.getAgentStatus().then((data) => data.forEach((a) => useAppStore.getState().updateAgent(a))).catch(() => {});
    api.getPipelineStatus().then((data) => data.forEach((p) => useAppStore.getState().updatePipeline(p))).catch(() => {});
    api.getTokenSummary().then(setTokenSummary).catch(() => {});
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <AlertBar/>

      <DashboardExtras />

      {/* Stat cards — one per cluster + WebSocket + Tokens */}
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${config.agents.clusters.length + 2}, 1fr)`, gap: 12 }}>
        {config.agents.clusters.map((cluster) => {
          const clAgents = agents.filter((a) => a.cluster === cluster.key);
          const running  = clAgents.filter((a) => a.status === "running");
          const hasError = clAgents.some((a) => a.status === "error");
          return (
            <StatCard
              key={cluster.key}
              label={cluster.label}
              value={`${running.length}/${clAgents.length}`}
              color={cluster.color}
              detail={hasError ? "Error — check alerts" : running.map((a) => a.role).join(", ") || "Idle"}
            />
          );
        })}
        <StatCard
          label="WebSocket"
          value={wsConnected ? "Live" : "Off"}
          color={wsConnected ? "var(--green)" : "#ef4444"}
        />
        <Tooltip title="Click to view token details">
          <div>
            <StatCard
              label="Tokens (Total)"
              value={tokenSummary ? formatTokens(tokenSummary.total_tokens) : "—"}
              color="#a855f7"
              detail={tokenSummary ? `$${tokenSummary.total_cost.toFixed(2)}` : ""}
              onClick={() => window.location.href = "/token-stats"}
            />
          </div>
        </Tooltip>
      </div>

      {/* Agent unified panel */}
      <AgentUnifiedPanel agents={agents} onSelectAgent={setSelectedAgentId}/>

      {/* System log */}
      <LogViewer/>

      {/* Agent detail drawer */}
      <AgentDetailDrawer agentId={selectedAgentId} onClose={() => setSelectedAgentId(null)}/>
    </div>
  );
}
