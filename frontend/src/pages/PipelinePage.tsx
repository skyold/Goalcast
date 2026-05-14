import { useEffect, useState, useCallback } from "react";
import { Spin, Drawer, Switch, InputNumber, Button, Empty } from "antd";
import {
  PlayCircleOutlined,
  SettingOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { useAppStore } from "../store/appStore";
import {
  getMatches,
  getPipelineStatus,
  runPipeline,
  getLeagues,
  getProviders,
  updateProviders,
  updateSchedule,
} from "../services/api";
import type {
  Match,
  League,
  ProvidersConfig,
  PipelineStatus,
} from "../types";
import MatchTable from "../components/MatchTable";

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

      {/* ── Main content: MatchTable ── */}
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
        <MatchTable matches={matches} />
      )}

      <SettingsDrawer
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        config={config}
        onConfigChange={setConfig}
      />
    </div>
  );
}
