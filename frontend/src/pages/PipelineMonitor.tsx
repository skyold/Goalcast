import { useEffect, useState, useCallback, useRef, Fragment } from "react";
import { Tag, Button, Empty, Spin, Drawer } from "antd";
import { ReloadOutlined, DownOutlined, RightOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import { PipelineMatchPanel } from "../components/MatchSourcePanel";
import type { PipelineLeague, PipelineMatch } from "../types";

const POLL_INTERVAL = 10000;

// ─── Time tab config ──────────────────────────────────────────────────────────

type TimeTab = "today" | "tomorrow" | "day_after" | "custom";

function getTabDate(tab: TimeTab, customDate: string): string {
  const today = dayjs();
  switch (tab) {
    case "today": return today.format("YYYY-MM-DD");
    case "tomorrow": return today.add(1, "day").format("YYYY-MM-DD");
    case "day_after": return today.add(2, "day").format("YYYY-MM-DD");
    case "custom": return customDate;
  }
}

const TIME_TABS: { key: TimeTab; label: string }[] = [
  { key: "today", label: "今天" },
  { key: "tomorrow", label: "明天" },
  { key: "day_after", label: "后天" },
  { key: "custom", label: "日期" },
];

// ─── Status helpers ───────────────────────────────────────────────────────────

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

// ─── Summary cells ────────────────────────────────────────────────────────────

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

// ─── Raw JSON Drawer ──────────────────────────────────────────────────────────

function RawDataDrawer({ raw, onClose }: { raw: { title: string; data: unknown } | null; onClose: () => void }) {
  return (
    <Drawer
      title={raw?.title ?? "原始数据"}
      placement="right"
      width={580}
      onClose={onClose}
      open={!!raw}
    >
      <pre style={{
        background: "#0a0a12", color: "var(--green)",
        padding: 16, borderRadius: 8, fontSize: 12,
        overflowX: "auto", whiteSpace: "pre-wrap",
        border: "1px solid var(--border)",
      }}>
        {raw ? JSON.stringify(raw.data, null, 2) : ""}
      </pre>
    </Drawer>
  );
}

// ─── Main PipelineMonitor ─────────────────────────────────────────────────────

export default function PipelineMonitor() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const pipelineStatus = useAppStore((s) => s.pipelineStatus);
  const activeLeagues = useAppStore((s) => s.activeLeagues);

  const [leagues, setLeagues] = useState<PipelineLeague[]>([]);
  const [matches, setMatches] = useState<PipelineMatch[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [leagueExpanded, setLeagueExpanded] = useState(false);

  // Time tab
  const todayStr = dayjs().format("YYYY-MM-DD");
  const [activeTimeTab, setActiveTimeTab] = useState<TimeTab>("today");
  const [customDate, setCustomDate] = useState(todayStr);

  // Expandable rows
  const [expandedMatchId, setExpandedMatchId] = useState<string | null>(null);
  const [expandedMatchFull, setExpandedMatchFull] = useState<Record<string, unknown> | null>(null);
  const [loadingMatchDetail, setLoadingMatchDetail] = useState(false);
  const [refreshingSource, setRefreshingSource] = useState<string | null>(null);

  // Raw JSON drawer
  const [rawDrawer, setRawDrawer] = useState<{ title: string; data: unknown } | null>(null);

  const initialTriggerRef = useRef(false);

  const activeLeagueNames = leagues.filter((l) => l.active).map((l) => l.chinese_name);
  const visibleLeagues = leagueExpanded ? leagues : leagues.slice(0, 8);

  const selectedDate = getTabDate(activeTimeTab, customDate);

  const fetchLeagues = useCallback(async () => {
    try {
      const res = await api.getPipelineLeagues();
      setLeagues(res.available);
    } catch { /* ignore */ }
  }, []);

  const fetchMatches = useCallback(async (date: string) => {
    setLoading(true);
    try {
      const res = await api.getPipelineMatches({ date_from: date, date_to: date });
      setMatches(res.items);
    } catch {
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchLeagues(); }, [fetchLeagues]);

  useEffect(() => {
    fetchMatches(selectedDate);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

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
    const timer = setInterval(() => fetchMatches(selectedDate), POLL_INTERVAL);
    return () => clearInterval(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate, fetchMatches]);

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

  const handleTimeTabChange = (tab: TimeTab) => {
    setActiveTimeTab(tab);
    setExpandedMatchId(null);
    setExpandedMatchFull(null);
  };

  const handleRowToggle = async (match: PipelineMatch) => {
    if (expandedMatchId === match.match_id) {
      setExpandedMatchId(null);
      setExpandedMatchFull(null);
      return;
    }
    setExpandedMatchId(match.match_id);
    setExpandedMatchFull(null);
    setLoadingMatchDetail(true);
    try {
      const full = await api.getMatchDetail(match.match_id);
      setExpandedMatchFull(full);
    } catch {
      setExpandedMatchFull({});
    } finally {
      setLoadingMatchDetail(false);
    }
  };

  const handleRefreshSource = async (matchId: string, source: string) => {
    setRefreshingSource(source);
    try {
      const result = await api.refreshMatchSource(matchId, source);
      setExpandedMatchFull((prev) => prev ? {
        ...prev,
        raw_data: {
          ...(prev.raw_data as Record<string, unknown> ?? {}),
          [source]: result.data,
        },
      } : prev);
    } catch { /* ignore */ }
    finally {
      setRefreshingSource(null);
    }
  };

  const cols = ["联赛", "主队", "客队", "开赛", "状态", "xG", "胜率", "推荐/EV"];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* League filter bar */}
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
          {!leagueExpanded && leagues.length > 8 && (
            <Tag
              onClick={() => setLeagueExpanded(true)}
              style={{ cursor: "pointer", opacity: 0.5, fontSize: 12 }}
            >
              ▼ 更多 ({leagues.length - 8})
            </Tag>
          )}
        </div>

        {/* Time tab + refresh row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {/* Time tabs */}
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            {TIME_TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => handleTimeTabChange(t.key)}
                style={{
                  padding: "4px 12px", fontSize: 12, borderRadius: 6, cursor: "pointer",
                  border: activeTimeTab === t.key ? "1px solid var(--accent-border)" : "1px solid var(--border)",
                  background: activeTimeTab === t.key ? "var(--accent-bg)" : "var(--nav-bg)",
                  color: activeTimeTab === t.key ? "var(--accent)" : "var(--text-muted)",
                  fontWeight: activeTimeTab === t.key ? 600 : 400,
                  transition: "all 0.15s",
                }}
              >
                {t.key === "custom" ? (
                  <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {t.label}
                    <input
                      type="date"
                      value={customDate}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        setCustomDate(e.target.value);
                        setActiveTimeTab("custom");
                      }}
                      style={{
                        background: "transparent", border: "none", outline: "none",
                        color: "inherit", fontSize: 11, fontFamily: "var(--font-mono)",
                        cursor: "pointer", width: 90,
                      }}
                    />
                  </span>
                ) : t.label}
              </button>
            ))}
            <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 8, fontFamily: "var(--font-mono)" }}>
              {selectedDate} · <strong style={{ color: "var(--accent)" }}>{matches.length}</strong> 场
            </span>
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

      {/* Connection status */}
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

      {/* Match table */}
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
                {cols.map((h) => (
                  <th key={h} style={{
                    padding: "8px 14px", textAlign: "left", fontSize: 11, fontWeight: 600,
                    color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em",
                    borderBottom: "1px solid var(--border)", whiteSpace: "nowrap",
                  }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matches.map((m, i) => {
                const isExpanded = expandedMatchId === m.match_id;
                const isLast = i === matches.length - 1;
                return (
                  <Fragment key={m.match_id}>
                    <tr
                      style={{
                        borderBottom: isExpanded ? "none" : (isLast ? "none" : "1px solid var(--border-subtle)"),
                        background: isExpanded ? "color-mix(in srgb, var(--nav-bg) 40%, transparent)" : "transparent",
                        cursor: "pointer",
                      }}
                      onMouseEnter={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "transparent";
                      }}
                      onClick={() => handleRowToggle(m)}
                    >
                      <td style={{ padding: "9px 14px", color: "var(--text)" }}>
                        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0 }}>
                            {isExpanded ? <DownOutlined /> : <RightOutlined />}
                          </span>
                          <span>{m.league_name}</span>
                        </span>
                      </td>
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

                    {isExpanded && (
                      <tr>
                        <td colSpan={cols.length} style={{ padding: 0, borderBottom: isLast ? "none" : "1px solid var(--border)" }}>
                          <PipelineMatchPanel
                            matchId={m.match_id}
                            pipelineSummary={m as unknown as Record<string, unknown>}
                            onViewRaw={(title, data) => setRawDrawer({ title, data })}
                            onRefresh={handleRefreshSource}
                            refreshingSource={refreshingSource}
                            fullRecord={expandedMatchFull}
                            loading={loadingMatchDetail}
                          />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <RawDataDrawer raw={rawDrawer} onClose={() => setRawDrawer(null)} />
    </div>
  );
}
