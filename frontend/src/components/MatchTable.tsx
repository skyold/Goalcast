import { useState } from "react";
import dayjs from "dayjs";
import type { Match } from "../types";
import SportMonksCard from "./SportMonksCard";
import OddsAlertsCard from "./OddsAlertsCard";

type MatchStatus = "pending" | "collected" | "analyzed" | "error" | "aborted";

const STATUS_META: Record<MatchStatus, { label: string; color: string }> = {
  pending:   { label: "pending",   color: "#6b7280" },
  collected: { label: "collected", color: "#00FF9D" },
  analyzed:  { label: "analyzed",  color: "#818cf8" },
  error:     { label: "error",     color: "#ef4444" },
  aborted:   { label: "aborted",   color: "#9ba3b8" },
};

function StatusBadge({ status }: { status: MatchStatus }) {
  const m = STATUS_META[status] ?? STATUS_META.pending;
  return (
    <span style={{
      fontSize: 10,
      fontWeight: 500,
      color: m.color,
      padding: "2px 6px",
      borderRadius: 3,
      border: `1px solid ${m.color}30`,
      background: `${m.color}10`,
      textTransform: "uppercase",
      letterSpacing: "0.04em",
    }}>
      {m.label}
    </span>
  );
}

interface MatchRowProps {
  match: Match;
  expanded: boolean;
  onToggle: () => void;
}

function MatchRow({ match, expanded, onToggle }: MatchRowProps) {
  const { metadata: m, status } = match;
  const kickoff = m.kickoff_time
    ? dayjs(m.kickoff_time).format("MM-DD HH:mm")
    : "--:--";

  return (
    <>
      <tr
        onClick={onToggle}
        style={{
          cursor: "pointer",
          background: expanded ? "rgba(0,255,157,0.03)" : "transparent",
          borderBottom: expanded ? "1px solid rgba(0,255,157,0.15)" : "1px solid rgba(255,255,255,0.04)",
          transition: "background 0.15s",
        }}
        onMouseEnter={(e) => {
          if (!expanded) (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.03)";
        }}
        onMouseLeave={(e) => {
          if (!expanded) (e.currentTarget as HTMLElement).style.background = "transparent";
        }}
      >
        <td style={{ padding: "10px 16px", width: 32 }}>
          <span style={{
            fontSize: 10,
            color: "var(--text-muted)",
            transition: "transform 0.2s",
            display: "inline-block",
            transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
          }}>
            ▶
          </span>
        </td>
        <td style={{
          padding: "10px 16px",
          fontSize: 12,
          fontWeight: 600,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
        }}>
          {m.league || "—"}
        </td>
        <td style={{
          padding: "10px 16px",
          fontSize: 13,
          fontWeight: 700,
          color: "var(--text)",
          width: "28%",
        }}>
          {m.home_team}
        </td>
        <td style={{
          padding: "10px 16px",
          fontSize: 13,
          fontWeight: 500,
          color: "var(--text-secondary)",
          width: "28%",
        }}>
          {m.away_team}
        </td>
        <td style={{
          padding: "10px 16px",
          fontSize: 12,
          color: "var(--text-secondary)",
          fontFamily: "var(--font-mono)",
          whiteSpace: "nowrap",
        }}>
          {kickoff}
        </td>
        <td style={{ padding: "10px 16px" }}>
          <StatusBadge status={status} />
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} style={{ padding: "16px 24px 24px", background: "rgba(0,255,157,0.02)" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {/* 流水线分析 */}
              <div style={{
                background: "var(--card-bg)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "12px 16px",
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", marginBottom: 6 }}>
                  🔴 流水线分析
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>
                  暂无分析数据
                </div>
              </div>

              {/* Provider Cards */}
              {match.raw_data && Object.keys(match.raw_data).length > 0 && (
                <>
                  {match.raw_data.sportmonks && (
                    <SportMonksCard data={match.raw_data.sportmonks} />
                  )}
                  {match.raw_data.oddsalerts && (
                    <OddsAlertsCard data={match.raw_data.oddsalerts} />
                  )}
                </>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

interface MatchTableProps {
  matches: Match[];
}

export default function MatchTable({ matches }: MatchTableProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleToggle = (matchId: string) => {
    setExpandedId((prev) => (prev === matchId ? null : matchId));
  };

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--border)",
      borderRadius: 12,
      overflow: "hidden",
    }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ padding: "12px 16px", width: 32 }}></th>
            <th style={{
              padding: "12px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "left",
            }}>
              联赛
            </th>
            <th style={{
              padding: "12px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "left",
            }}>
              主队
            </th>
            <th style={{
              padding: "12px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "left",
            }}>
              客队
            </th>
            <th style={{
              padding: "12px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "left",
            }}>
              开赛
            </th>
            <th style={{
              padding: "12px 16px",
              fontSize: 11,
              fontWeight: 600,
              color: "var(--text-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              textAlign: "left",
            }}>
              状态
            </th>
          </tr>
        </thead>
        <tbody>
          {matches.map((match) => (
            <MatchRow
              key={match.match_id}
              match={match}
              expanded={expandedId === match.match_id}
              onToggle={() => handleToggle(match.match_id)}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}
