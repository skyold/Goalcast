import { useEffect, useState, useCallback } from "react";
import { Spin, Drawer, Switch, InputNumber, Button, Tag, Empty } from "antd";
import {
  PlayCircleOutlined,
  SettingOutlined,
  CloseOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { useAppStore } from "../store/appStore";
import {
  getMatches,
  getMatch,
  getPipelineStatus,
  runPipeline,
  getLeagues,
  getProviders,
  updateProviders,
  updateSchedule,
} from "../services/api";
import type {
  Match,
  MatchStatus,
  League,
  ProvidersConfig,
  PipelineStatus,
} from "../types";

// ─── Constants ────────────────────────────────────────────────────────────────

const POLL_INTERVAL = 12_000;

type DateTab = "today" | "tomorrow" | "day_after" | "custom";

const DATE_TABS: { key: DateTab; label: string }[] = [
  { key: "today", label: "今天" },
  { key: "tomorrow", label: "明天" },
  { key: "day_after", label: "后天" },
  { key: "custom", label: "日期" },
];

function tabToDate(tab: DateTab, custom: string): string {
  if (tab === "today") return dayjs().format("YYYY-MM-DD");
  if (tab === "tomorrow") return dayjs().add(1, "day").format("YYYY-MM-DD");
  if (tab === "day_after") return dayjs().add(2, "day").format("YYYY-MM-DD");
  return custom;
}

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_META: Record<MatchStatus, { label: string; color: string; dot: string }> = {
  pending:   { label: "待处理", color: "var(--text-muted)",    dot: "#6b7280" },
  collected: { label: "已收集", color: "var(--accent)",        dot: "#00FF9D" },
  analyzed:  { label: "已分析", color: "#6366f1",              dot: "#818cf8" },
  error:     { label: "错误",   color: "#ef4444",              dot: "#ef4444" },
};

function StatusBadge({ status }: { status: MatchStatus }) {
  const m = STATUS_META[status] ?? STATUS_META.pending;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontSize: 11, fontWeight: 600, color: m.color,
      padding: "2px 8px", borderRadius: 100,
      border: `1px solid ${m.dot}30`,
      background: `${m.dot}12`,
      whiteSpace: "nowrap",
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: "50%",
        background: m.dot,
        boxShadow: status === "collected" || status === "analyzed" ? `0 0 5px ${m.dot}` : "none",
      }} />
      {m.label}
    </span>
  );
}

// ─── Confidence bar ───────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 70 ? "#00FF9D" : pct >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 3, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color, fontFamily: "var(--font-mono)", minWidth: 28 }}>{pct}%</span>
    </div>
  );
}

// ─── Match card ───────────────────────────────────────────────────────────────

interface MatchCardProps {
  match: Match;
  onClick: () => void;
  selected: boolean;
}

function MatchCard({ match, onClick, selected }: MatchCardProps) {
  const { metadata: m, analysis: a, status } = match;
  const kickoff = m.kickoff_time ? dayjs(m.kickoff_time).format("HH:mm") : "--:--";
  const hasAnalysis = status === "analyzed" && (a.ah_recommendation || a.home_xg != null);

  return (
    <div
      onClick={onClick}
      style={{
        background: selected ? "rgba(0,255,157,0.05)" : "var(--card-bg)",
        border: `1px solid ${selected ? "rgba(0,255,157,0.25)" : "var(--border)"}`,
        borderRadius: 10,
        padding: "14px 16px",
        cursor: "pointer",
        transition: "border-color 0.15s, background 0.15s",
        display: "flex",
        flexDirection: "column",
        gap: 10,
      }}
      onMouseEnter={(e) => {
        if (!selected) (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.15)";
      }}
      onMouseLeave={(e) => {
        if (!selected) (e.currentTarget as HTMLElement).style.borderColor = "var(--border)";
      }}
    >
      {/* League + time */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{
          fontSize: 10, fontWeight: 600, color: "var(--text-muted)",
          textTransform: "uppercase", letterSpacing: "0.08em",
        }}>
          {m.league || "—"}
        </span>
        <span style={{ fontSize: 11, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
          {m.kickoff_time ? dayjs(m.kickoff_time).format("MM-DD") : ""} {kickoff}
        </span>
      </div>

      {/* Teams */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", flex: 1 }}>{m.home_team}</span>
        <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)", flexShrink: 0 }}>VS</span>
        <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-secondary)", flex: 1, textAlign: "right" }}>{m.away_team}</span>
      </div>

      {/* Analysis row */}
      {hasAnalysis ? (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
          {/* xG */}
          {a.home_xg != null && a.away_xg != null && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              xG <span style={{ color: "var(--text)" }}>{a.home_xg.toFixed(2)}</span>
              {" · "}
              <span style={{ color: "var(--text)" }}>{a.away_xg.toFixed(2)}</span>
            </span>
          )}
          {/* Recommendation */}
          {a.ah_recommendation && (
            <Tag style={{
              borderColor: "rgba(0,255,157,0.3)", background: "rgba(0,255,157,0.08)",
              color: "var(--accent)", fontSize: 11, fontWeight: 700, margin: 0,
            }}>
              {a.ah_recommendation}
            </Tag>
          )}
          {/* Kelly */}
          {a.kelly_fraction != null && (
            <span style={{ fontSize: 11, color: "#f59e0b", fontFamily: "var(--font-mono)" }}>
              Kelly {(a.kelly_fraction * 100).toFixed(1)}%
            </span>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <StatusBadge status={status} />
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
            {Object.keys(m.provider_ids ?? {}).join(" · ") || "—"}
          </span>
        </div>
      )}

      {/* Confidence */}
      {hasAnalysis && a.confidence != null && (
        <ConfidenceBar value={a.confidence} />
      )}

      {/* Status on analyzed cards */}
      {hasAnalysis && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <StatusBadge status={status} />
          {m.collected_at && (
            <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {dayjs(m.collected_at).format("HH:mm")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Detail panel ─────────────────────────────────────────────────────────────

function MatchDetail({ match, onClose }: { match: Match; onClose: () => void }) {
  const { metadata: m, analysis: a } = match;
  const rows: { label: string; value: string | number | null | undefined }[] = [
    { label: "主队 xG", value: a.home_xg?.toFixed(2) },
    { label: "客队 xG", value: a.away_xg?.toFixed(2) },
    { label: "亚盘推荐", value: a.ah_recommendation },
    { label: "置信度", value: a.confidence != null ? `${(a.confidence * 100).toFixed(0)}%` : null },
    { label: "Kelly 比例", value: a.kelly_fraction != null ? `${(a.kelly_fraction * 100).toFixed(1)}%` : null },
  ];
  const providers = Object.entries(m.provider_ids ?? {});

  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--accent-border)",
      borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 16,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            {m.league}
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: "var(--text)" }}>
            {m.home_team} <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>vs</span> {m.away_team}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginTop: 4, fontFamily: "var(--font-mono)" }}>
            {m.kickoff_time ? dayjs(m.kickoff_time).format("YYYY-MM-DD HH:mm") : "—"}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", padding: 4 }}
        >
          <CloseOutlined />
        </button>
      </div>

      {/* Analysis table */}
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr",
        gap: 8,
      }}>
        {rows.filter(r => r.value != null).map((r) => (
          <div key={r.label} style={{
            background: "var(--nav-bg)", borderRadius: 8, padding: "10px 14px",
          }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              {r.label}
            </div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "var(--accent)", fontFamily: "var(--font-mono)" }}>
              {r.value}
            </div>
          </div>
        ))}
      </div>

      {/* Providers */}
      {providers.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 8 }}>数据源</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {providers.map(([name, id]) => (
              <span key={name} style={{
                fontSize: 11, padding: "3px 10px",
                borderRadius: 100, border: "1px solid var(--border)",
                color: "var(--text-secondary)", fontFamily: "var(--font-mono)",
              }}>
                {name}:{id}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Status */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <StatusBadge status={match.status} />
        {m.collected_at && (
          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            收集于 {dayjs(m.collected_at).format("HH:mm")}
          </span>
        )}
      </div>
    </div>
  );
}

// ─── Settings drawer ──────────────────────────────────────────────────────────

function SettingsDrawer({
  open, onClose, config, onConfigChange,
}: {
  open: boolean;
  onClose: () => void;
  config: ProvidersConfig | null;
  onConfigChange: (c: ProvidersConfig) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [intervalVal, setIntervalVal] = useState<number>(1);

  useEffect(() => {
    if (config) setIntervalVal(config.schedule.interval_hours);
  }, [config]);

  const handleProviderToggle = async (name: string, enabled: boolean) => {
    if (!config) return;
    setSaving(true);
    try {
      const res = await updateProviders({ providers: { [name]: enabled } });
      onConfigChange(res.config);
    } finally {
      setSaving(false);
    }
  };

  const handleAnalystToggle = async (enabled: boolean) => {
    if (!config) return;
    setSaving(true);
    try {
      const res = await updateProviders({ analyst: enabled });
      onConfigChange(res.config);
    } finally {
      setSaving(false);
    }
  };

  const handleScheduleSave = async () => {
    setSaving(true);
    try {
      await updateSchedule(intervalVal);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Drawer
      title="设置"
      placement="right"
      width={320}
      onClose={onClose}
      open={open}
      styles={{ body: { padding: 20 } }}
    >
      {config ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Providers */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
              数据源
            </div>
            {Object.entries(config.providers).map(([name, enabled]) => (
              <div key={name} style={{
                display: "flex", justifyContent: "space-between", alignItems: "center",
                padding: "10px 0", borderBottom: "1px solid var(--border)",
              }}>
                <span style={{ fontSize: 13, color: "var(--text)", textTransform: "capitalize" }}>{name}</span>
                <Switch
                  size="small"
                  checked={enabled}
                  onChange={(v) => handleProviderToggle(name, v)}
                  disabled={saving}
                />
              </div>
            ))}
          </div>

          {/* Analyst */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
              分析模块
            </div>
            <div style={{
              display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "10px 0", borderBottom: "1px solid var(--border)",
            }}>
              <div>
                <div style={{ fontSize: 13, color: "var(--text)" }}>Analyst Agent</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>使用 Claude 进行比赛分析</div>
              </div>
              <Switch
                size="small"
                checked={config.analyst.enabled}
                onChange={handleAnalystToggle}
                disabled={saving}
              />
            </div>
          </div>

          {/* Schedule */}
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
              定时执行
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <InputNumber
                min={1}
                max={24}
                value={intervalVal}
                onChange={(v) => v != null && setIntervalVal(v)}
                style={{ width: 80 }}
                size="small"
              />
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>小时/次</span>
              <Button size="small" onClick={handleScheduleSave} loading={saving}>保存</Button>
            </div>
          </div>
        </div>
      ) : (
        <Spin style={{ display: "block", margin: "40px auto" }} />
      )}
    </Drawer>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const pipelineStatusStore = useAppStore((s) => s.pipelineStatus);
  const lastWsEvent = useAppStore((s) => s.lastWsEvent);

  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [pipelineStatus, setPipelineStatus] = useState<PipelineStatus | null>(pipelineStatusStore);
  const [leagues, setLeagues] = useState<League[]>([]);
  const [selectedLeague, setSelectedLeague] = useState<string>("");
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Date tabs
  const [dateTab, setDateTab] = useState<DateTab>("today");
  const [customDate, setCustomDate] = useState(dayjs().format("YYYY-MM-DD"));
  const selectedDate = tabToDate(dateTab, customDate);

  // Settings
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [config, setConfig] = useState<ProvidersConfig | null>(null);

  // ── fetch helpers ──────────────────────────────────────────────────────────

  const fetchMatches = useCallback(async () => {
    setLoading(true);
    try {
      const params: { date?: string; league?: string } = { date: selectedDate };
      if (selectedLeague) params.league = selectedLeague;
      const res = await getMatches(params);
      setMatches(res.items);
    } catch {
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedLeague]);

  const fetchPipelineStatus = useCallback(async () => {
    try {
      const s = await getPipelineStatus();
      setPipelineStatus(s);
    } catch { /* ignore */ }
  }, []);

  // ── mount ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    fetchMatches();
    fetchPipelineStatus();
    getLeagues().then((r) => setLeagues(r.available)).catch(() => {});
  }, [fetchMatches, fetchPipelineStatus]);

  useEffect(() => {
    const t = setInterval(fetchMatches, POLL_INTERVAL);
    return () => clearInterval(t);
  }, [fetchMatches]);

  // Refresh on WS events
  useEffect(() => {
    if (!lastWsEvent) return;
    if (
      lastWsEvent.type === "pipeline_complete" ||
      lastWsEvent.type === "match_analyzed" ||
      lastWsEvent.type === "match_collected"
    ) {
      fetchMatches();
      fetchPipelineStatus();
    }
  }, [lastWsEvent, fetchMatches, fetchPipelineStatus]);

  // ── handlers ──────────────────────────────────────────────────────────────

  const handleTrigger = async () => {
    setTriggering(true);
    try {
      await runPipeline();
      setTimeout(fetchPipelineStatus, 1000);
    } catch { /* ignore */ }
    finally { setTriggering(false); }
  };

  const handleMatchClick = async (match: Match) => {
    if (selectedMatch?.match_id === match.match_id) {
      setSelectedMatch(null);
      return;
    }
    setDetailLoading(true);
    setSelectedMatch(match);
    try {
      const full = await getMatch(match.match_id);
      setSelectedMatch(full);
    } catch { /* keep summary */ }
    finally { setDetailLoading(false); }
  };

  const handleSettingsOpen = async () => {
    setSettingsOpen(true);
    if (!config) {
      try {
        const c = await getProviders();
        setConfig(c);
      } catch { /* ignore */ }
    }
  };

  // ── derived ───────────────────────────────────────────────────────────────

  const isRunning = pipelineStatusStore?.running ?? pipelineStatus?.running ?? false;
  const lastResult = pipelineStatusStore?.last_result ?? pipelineStatus?.last_result;
  const analyzed = matches.filter((m) => m.status === "analyzed");

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 1280, margin: "0 auto" }}>

      {/* ── Top status bar ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "var(--card-bg)", border: "1px solid var(--border)",
        borderRadius: 10, padding: "12px 18px", gap: 16, flexWrap: "wrap",
      }}>
        {/* Left: WS + pipeline status */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{
              width: 7, height: 7, borderRadius: "50%",
              background: wsConnected ? "#00FF9D" : "#ef4444",
              boxShadow: wsConnected ? "0 0 6px #00FF9D" : "none",
            }} />
            <span style={{ fontSize: 11, color: wsConnected ? "#00FF9D" : "#ef4444", fontFamily: "var(--font-mono)" }}>
              {wsConnected ? "Live" : "Offline"}
            </span>
          </div>

          <div style={{ width: 1, height: 14, background: "var(--border)" }} />

          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {isRunning && (
              <span style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                fontSize: 11, color: "#f59e0b", fontFamily: "var(--font-mono)",
              }}>
                <span style={{
                  width: 6, height: 6, borderRadius: "50%", background: "#f59e0b",
                  animation: "pulse 1.2s ease-in-out infinite",
                }} />
                Running
              </span>
            )}
            {!isRunning && lastResult && (
              <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                上次: {lastResult.discovered}场 · {lastResult.collected}收集 · {lastResult.analyzed}分析
              </span>
            )}
            {!isRunning && !lastResult && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>待机</span>
            )}
          </div>
        </div>

        {/* Right: stats + buttons */}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            <span style={{ color: "var(--text)", fontWeight: 700 }}>{matches.length}</span> 场
            {analyzed.length > 0 && (
              <> · <span style={{ color: "var(--accent)", fontWeight: 700 }}>{analyzed.length}</span> 已分析</>
            )}
          </span>

          <Button
            size="small"
            icon={<SettingOutlined />}
            onClick={handleSettingsOpen}
            style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}
          />

          <Button
            size="small"
            icon={isRunning ? <ReloadOutlined spin /> : <PlayCircleOutlined />}
            onClick={handleTrigger}
            loading={triggering}
            style={{
              borderColor: "rgba(0,255,157,0.3)",
              background: "rgba(0,255,157,0.06)",
              color: "var(--accent)",
              fontWeight: 600,
            }}
          >
            {isRunning ? "运行中…" : "执行"}
          </Button>
        </div>
      </div>

      {/* ── Filter bar ── */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap",
      }}>
        {/* Date tabs */}
        {DATE_TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setDateTab(t.key)}
            style={{
              padding: "5px 12px", fontSize: 12, borderRadius: 7, cursor: "pointer",
              border: dateTab === t.key ? "1px solid rgba(0,255,157,0.35)" : "1px solid var(--border)",
              background: dateTab === t.key ? "rgba(0,255,157,0.07)" : "var(--nav-bg)",
              color: dateTab === t.key ? "var(--accent)" : "var(--text-muted)",
              fontWeight: dateTab === t.key ? 600 : 400,
              transition: "all 0.12s",
            }}
          >
            {t.key === "custom" ? (
              <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                {t.label}
                <input
                  type="date"
                  value={customDate}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => { setCustomDate(e.target.value); setDateTab("custom"); }}
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

        <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
          {selectedDate}
        </span>

        <div style={{ flex: 1 }} />

        {/* League filter */}
        <select
          value={selectedLeague}
          onChange={(e) => setSelectedLeague(e.target.value)}
          style={{
            padding: "5px 10px", fontSize: 12, borderRadius: 7, cursor: "pointer",
            border: "1px solid var(--border)", background: "var(--nav-bg)",
            color: selectedLeague ? "var(--text)" : "var(--text-muted)",
            outline: "none", maxWidth: 180,
          }}
        >
          <option value="">全部联赛</option>
          {leagues.map((l) => (
            <option key={l.id} value={l.chinese_name}>{l.chinese_name}</option>
          ))}
        </select>
      </div>

      {/* ── Main content: card grid + detail ── */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
        {/* Match grid */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {loading && matches.length === 0 ? (
            <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
              <Spin />
            </div>
          ) : matches.length === 0 ? (
            <Empty
              description="暂无比赛数据，请点击「执行」触发 Pipeline"
              style={{ padding: 60, color: "var(--text-muted)" }}
            />
          ) : (
            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 12,
            }}>
              {matches.map((m) => (
                <MatchCard
                  key={m.match_id}
                  match={m}
                  selected={selectedMatch?.match_id === m.match_id}
                  onClick={() => handleMatchClick(m)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail panel */}
        {selectedMatch && (
          <div style={{ width: 340, flexShrink: 0, position: "sticky", top: 0 }}>
            {detailLoading ? (
              <div style={{
                background: "var(--card-bg)", border: "1px solid var(--border)",
                borderRadius: 12, padding: 40, display: "flex", justifyContent: "center",
              }}>
                <Spin />
              </div>
            ) : (
              <MatchDetail match={selectedMatch} onClose={() => setSelectedMatch(null)} />
            )}
          </div>
        )}
      </div>

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        config={config}
        onConfigChange={setConfig}
      />
    </div>
  );
}
