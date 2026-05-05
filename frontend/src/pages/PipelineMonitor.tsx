import { useEffect, useState, useCallback, useRef } from "react";
import { Tag, Button, Empty, Spin, Drawer } from "antd";
import { ReloadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { PipelineLeague, PipelineMatch } from "../types";

const POLL_INTERVAL = 10000;

function getStatusColor(status: string): string {
  switch (status) {
    case "pending": return "default";
    case "analyzing": return "processing";
    case "trading": return "orange";
    case "reviewed": return "green";
    case "reported": return "blue";
    case "error": return "red";
    case "rejected": return "red";
    default: return "default";
  }
}

function XGCell({ homeXg, awayXg }: { homeXg?: number; awayXg?: number }) {
  if (homeXg == null || awayXg == null) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const homeColor = homeXg >= awayXg ? "var(--accent)" : "var(--text-secondary)";
  const awayColor = awayXg > homeXg ? "var(--accent)" : "var(--text-secondary)";
  return (
    <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
      <span style={{ color: homeColor, fontWeight: 600 }}>{homeXg.toFixed(2)}</span>
      {" : "}
      <span style={{ color: awayColor, fontWeight: 600 }}>{awayXg.toFixed(2)}</span>
    </span>
  );
}

function ProbBar({ probs }: { probs?: { home_win: number; draw: number; away_win: number } }) {
  if (!probs) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const h = Math.round(probs.home_win * 100);
  const d = Math.round(probs.draw * 100);
  const a = Math.round(probs.away_win * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ display: "flex", height: 8, borderRadius: 2, overflow: "hidden", width: 100, gap: 1 }}>
        <div style={{ flex: h, background: "var(--accent)" }} />
        <div style={{ flex: d, background: "var(--text-muted)" }} />
        <div style={{ flex: a, background: "#3b82f6" }} />
      </div>
      <span style={{ fontSize: 10, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
        {h}/{d}/{a}
      </span>
    </div>
  );
}

function RecEVCell({ rec, ev }: { rec?: string; ev?: number }) {
  const recLabel = rec || "";
  const evColor = ev == null ? "var(--text-muted)" : ev > 0.05 ? "var(--accent)" : ev > 0 ? "var(--orange)" : "var(--red)";
  const evLabel = ev != null ? `${ev >= 0 ? "+" : ""}${ev.toFixed(3)}` : "—";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      {recLabel ? (
        <span style={{ fontSize: 11, padding: "1px 6px", borderRadius: 3, background: "var(--accent-bg)", color: "var(--accent)", border: "1px solid var(--accent-border)", fontFamily: "var(--font-mono)" }}>
          {recLabel}
        </span>
      ) : <span style={{ color: "var(--text-muted)", fontSize: 11 }}>—</span>}
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 600, color: evColor }}>
        {evLabel}
      </span>
    </div>
  );
}

function MatchDetailDrawer({ match, onClose }: { match: PipelineMatch | null; onClose: () => void }) {
  if (!match) return null;
  return (
    <Drawer
      title={`${match.home_team} vs ${match.away_team}`}
      placement="right"
      width={500}
      onClose={onClose}
      open={!!match}
    >
      <pre style={{ background: "#0a0a12", color: "var(--green)", padding: 16, borderRadius: 8, fontSize: 12, overflowX: "auto", whiteSpace: "pre-wrap", border: "1px solid var(--border)" }}>
        {JSON.stringify(match, null, 2)}
      </pre>
    </Drawer>
  );
}

export default function PipelineMonitor() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const pipelineStatus = useAppStore((s) => s.pipelineStatus);
  const activeLeagues = useAppStore((s) => s.activeLeagues);

  const [leagues, setLeagues] = useState<PipelineLeague[]>([]);
  const [matches, setMatches] = useState<PipelineMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<PipelineMatch | null>(null);
  const initialTriggerRef = useRef(false);

  const threeDaysLater = dayjs().add(3, "day").format("YYYY-MM-DD");
  const todayStr = dayjs().format("YYYY-MM-DD");
  const [dateFrom, setDateFrom] = useState(todayStr);
  const [dateTo, setDateTo] = useState(threeDaysLater);

  const activeLeagueNames = leagues.filter((l) => l.active).map((l) => l.chinese_name);
  const visibleLeagues = expanded ? leagues : leagues.slice(0, 8);

  const fetchLeagues = useCallback(async () => {
    try {
      const res = await api.getPipelineLeagues();
      setLeagues(res.available);
    } catch { /* ignore */ }
  }, []);

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getPipelineMatches({ date_from: dateFrom, date_to: dateTo });
      setMatches(res.items);
    } catch {
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, [dateFrom, dateTo]);

  useEffect(() => { fetchLeagues(); }, [fetchLeagues]);
  useEffect(() => { fetchMatches(); }, [fetchMatches]);

  useEffect(() => {
    if (initialTriggerRef.current) return;
    if (activeLeagueNames.length === 0) return;
    initialTriggerRef.current = true;
    setTriggering(true);
    api.triggerPipeline().finally(() => {
      setTimeout(() => setTriggering(false), 2000);
    });
  }, [activeLeagueNames]);

  useEffect(() => {
    const timer = setInterval(fetchMatches, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [fetchMatches]);

  const handleLeagueToggle = async (cn: string) => {
    const newActive = activeLeagueNames.includes(cn)
      ? activeLeagueNames.filter((l) => l !== cn)
      : [...activeLeagueNames, cn];
    try {
      await api.updatePipelineLeagues(newActive);
      setLeagues((prev) =>
        prev.map((l) => ({ ...l, active: newActive.includes(l.chinese_name) }))
      );
    } catch { /* ignore */ }
  };

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await api.triggerPipeline();
    } catch { /* ignore */ }
    setTimeout(() => setTriggering(false), 2000);
  };

  const handleDateFromChange = (val: string) => {
    setDateFrom(val);
    if (val > dateTo) setDateTo(val);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* League Bar */}
      <div style={{
        background: "var(--card-bg)", border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)", padding: "14px 18px",
      }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
          {visibleLeagues.map((l) => (
            <Tag.CheckableTag
              key={l.id}
              checked={l.active}
              onChange={() => handleLeagueToggle(l.chinese_name)}
              style={{
                border: l.active ? "1px solid var(--accent-border)" : "1px solid var(--border)",
                background: l.active ? "var(--accent-bg)" : "var(--nav-bg)",
                color: l.active ? "var(--accent)" : "var(--text-muted)",
                fontSize: 12, fontWeight: 500,
              }}
            >
              {l.chinese_name}
            </Tag.CheckableTag>
          ))}
          {!expanded && leagues.length > 8 && (
            <Tag
              onClick={() => setExpanded(true)}
              style={{ cursor: "pointer", opacity: 0.5, fontSize: 12 }}
            >
              ▼ 更多 ({leagues.length - 8})
            </Tag>
          )}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, color: "var(--text-secondary)" }}>
          <span>激活: <strong style={{ color: "var(--accent)" }}>{activeLeagueNames.join(", ") || "无"}</strong></span>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => handleDateFromChange(e.target.value)}
              style={{
                background: "var(--nav-bg)", border: "1px solid var(--border)", borderRadius: 6,
                color: "var(--text)", padding: "4px 8px", fontSize: 12, fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            />
            <span style={{ color: "var(--text-muted)" }}>→</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              style={{
                background: "var(--nav-bg)", border: "1px solid var(--border)", borderRadius: 6,
                color: "var(--text)", padding: "4px 8px", fontSize: 12, fontFamily: "var(--font-mono)",
                outline: "none",
              }}
            />
            <span>· <strong style={{ color: "var(--accent)" }}>{matches.length}</strong> 场比赛</span>
          </div>
          <Button
            size="small"
            icon={<ReloadOutlined spin={triggering} />}
            onClick={handleTrigger}
            loading={triggering}
            style={{ borderColor: "var(--accent-border)", color: "var(--accent)" }}
          >
            强制刷新
          </Button>
        </div>
      </div>

      {/* Pipeline status bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 6,
        padding: "4px 0", fontSize: 11, color: "var(--text-muted)",
      }}>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: wsConnected ? "var(--green)" : "#ef4444",
          boxShadow: wsConnected ? "0 0 6px var(--green)" : "none",
        }} />
        <span>{wsConnected ? "Connected" : "Disconnected"}</span>
        {activeLeagues.length > 0 && (
          <span>· <Tag color="processing" style={{ fontSize: 10 }}>{pipelineStatus || "Idle"}</Tag></span>
        )}
      </div>

      {/* Table */}
      {loading && matches.length === 0 ? (
        <Spin style={{ display: "block", margin: "40px auto" }} />
      ) : matches.length === 0 ? (
        <Empty description="暂无比赛数据。请选择联赛后等待 Orchestrator 拉取，或点击强制刷新。" style={{ padding: 40 }} />
      ) : (
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)", overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--nav-bg)" }}>
                {["联赛", "主队", "客队", "开赛", "状态", "xG (主:客)", "胜率", "推荐 / EV"].map((h) => (
                  <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", borderBottom: "1px solid var(--border)", whiteSpace: "nowrap" }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matches.map((m, i) => (
                <tr
                  key={m.match_id}
                  style={{ borderBottom: i < matches.length - 1 ? "1px solid var(--border-subtle)" : "none", cursor: "pointer" }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.background = "var(--hover-bg)")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.background = "transparent")}
                  onClick={() => setSelectedMatch(m)}
                >
                  <td style={{ padding: "9px 14px", color: "var(--text)" }}>{m.league_name}</td>
                  <td style={{ padding: "9px 14px", color: "var(--text)", fontWeight: 600 }}>{m.home_team}</td>
                  <td style={{ padding: "9px 14px", color: "var(--text-secondary)" }}>{m.away_team}</td>
                  <td style={{ padding: "9px 14px", fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--text-secondary)" }}>
                    {m.kickoff_time ? dayjs(m.kickoff_time).format("MM-DD HH:mm") : "—"}
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <Tag color={getStatusColor(m.status)} style={{ fontSize: 10, fontWeight: 600 }}>{m.status}</Tag>
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <XGCell homeXg={m.home_xg} awayXg={m.away_xg} />
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <ProbBar probs={m.result_probs} />
                  </td>
                  <td style={{ padding: "9px 14px" }}>
                    <RecEVCell rec={m.recommendation} ev={m.ev} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MatchDetailDrawer match={selectedMatch} onClose={() => setSelectedMatch(null)} />
    </div>
  );
}
