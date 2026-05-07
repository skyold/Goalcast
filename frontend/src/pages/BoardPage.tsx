import { useEffect, useState, useCallback, Fragment, type ReactNode } from "react";
import { Tabs, Drawer, Button, Pagination, Spin, Empty, Badge, Tag, Tooltip, message } from "antd";
import { ReloadOutlined, CodeOutlined, DownOutlined, RightOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Prism from "prismjs";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useConfig } from "../config";
import { useAppStore } from "../store/appStore";
import { api } from "../services/api";
import type { JsonRecord, BoardTab, BoardTabSource, DetailTab, ColumnDef } from "../types";

dayjs.extend(relativeTime);

// ─── Utility ──────────────────────────────────────────────────────────────────

function getByPath(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

function fmt(n: unknown, d = 2): string {
  const v = Number(n);
  return isNaN(v) ? "—" : v.toFixed(d);
}

function fmtPct(n: unknown): string {
  const v = Number(n);
  if (isNaN(v)) return "—";
  return (v > 1 ? v : v * 100).toFixed(1) + "%";
}

// ─── CellRenderer ─────────────────────────────────────────────────────────────

function CellRenderer({ col, value }: { col: ColumnDef; value: unknown }) {
  if (value == null) return <span>—</span>;
  const render = col.render ?? "text";
  switch (render) {
    case "status_badge": {
      const cfg = col.status_map?.[String(value)];
      if (cfg) return <Badge color={cfg.color} text={cfg.text} />;
      return <Tag>{String(value)}</Tag>;
    }
    case "number_precision": {
      const n = Number(value);
      return isNaN(n) ? <span>{String(value)}</span> : <span>{n.toFixed(col.precision ?? 2)}</span>;
    }
    case "percentage_color": {
      const n = Number(value);
      if (isNaN(n)) return <span>{String(value)}</span>;
      return <span style={{ color: n >= 0 ? "var(--green)" : "var(--red)" }}>{(n * 100).toFixed(2)}%</span>;
    }
    case "relative_time": return <span>{dayjs(String(value)).fromNow()}</span>;
    case "date_time": return <span>{dayjs(String(value)).format("YYYY-MM-DD HH:mm:ss")}</span>;
    case "code_snippet":
      return <code style={{ fontSize: 11, background: "var(--nav-bg)", padding: "2px 4px", borderRadius: 4 }}>{String(value)}</code>;
    default: return <span>{String(value)}</span>;
  }
}

// ─── DetailTabRenderer ────────────────────────────────────────────────────────

function DetailTabRenderer({ tab, data }: { tab: DetailTab; data: Record<string, unknown> }) {
  const content = (getByPath(data, tab.field) as string) || "";
  if (tab.format === "markdown") {
    return (
      <div className="markdown-body" style={{ padding: 16 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
      </div>
    );
  }
  if (tab.format === "code") {
    const html = Prism.highlight(
      content,
      Prism.languages[tab.language || "javascript"] || Prism.languages.javascript,
      tab.language || "javascript"
    );
    return (
      <pre style={{ margin: 0, padding: 16, background: "var(--nav-bg)", overflow: "auto" }}>
        <code dangerouslySetInnerHTML={{ __html: html }} />
      </pre>
    );
  }
  return (
    <pre style={{ margin: 0, padding: 16, background: "var(--nav-bg)", overflow: "auto" }}>
      <code>{JSON.stringify(data[tab.field] || data, null, 2)}</code>
    </pre>
  );
}

// ─── Source data helpers ──────────────────────────────────────────────────────

function flattenAnalysis(a: Record<string, unknown>): Record<string, unknown> {
  if (a.home_xg != null || a.away_xg != null) return a;
  const v40 = a["v4.0"] as Record<string, unknown> | undefined;
  if (v40?.home_xg != null || v40?.away_xg != null) return v40!;
  const pm = a.predictive_metrics as Record<string, unknown> | undefined;
  if (pm?.home_xg != null) return pm!;
  return a;
}

interface FtOdds {
  bookmaker: string;
  home?: { opening: number; closing: number };
  draw?: { opening: number; closing: number };
  away?: { opening: number; closing: number };
}

function extractFtOdds(rows: Array<Record<string, unknown>>): FtOdds | null {
  const ft = rows.filter((o) => o.market_key === "ft_result");
  for (const bm of ["Bet365", "Pinnacle", "1xBet", "WilliamHill"]) {
    const bmRows = ft.filter((o) => o.bookmaker_name === bm);
    if (!bmRows.length) continue;
    const r: FtOdds = { bookmaker: bm };
    for (const o of bmRows) {
      const outcome = String(o.outcome || "");
      const opening = o.opening ? Number(o.opening) : 0;
      const closing = o.closing ? Number(o.closing) : 0;
      const pair = { opening: opening || closing, closing: closing || opening };
      if (outcome === "home") r.home = pair;
      else if (outcome === "draw") r.draw = pair;
      else if (outcome === "away") r.away = pair;
    }
    if (r.home || r.draw || r.away) return r;
  }
  return null;
}

// ─── Metric item (inline label: value) ───────────────────────────────────────

function MetricItem({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
      <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>{label}:</span>
      <span style={{
        fontSize: 12, fontFamily: "var(--font-mono)",
        color: highlight ? "var(--accent)" : "var(--text-secondary)",
        fontWeight: highlight ? 600 : 400,
      }}>{value}</span>
    </div>
  );
}

// ─── SourceCard (full-width horizontal strip) ─────────────────────────────────

interface SourceCardProps {
  title: string;
  icon?: string;
  collectedAt?: string;
  children?: ReactNode;
  onViewRaw?: () => void;
  onRefresh?: () => void;
  refreshing?: boolean;
  refreshDisabled?: boolean;
  refreshDisabledTip?: string;
  noData?: boolean;
}

function SourceCard({
  title, icon, collectedAt, children, onViewRaw, onRefresh,
  refreshing, refreshDisabled, refreshDisabledTip, noData,
}: SourceCardProps) {
  return (
    <div style={{
      width: "100%",
      display: "flex", alignItems: "center", gap: 12,
      background: "var(--card-bg)", border: "1px solid var(--border)",
      borderRadius: "var(--radius-md)", padding: "8px 12px",
    }}>
      {/* Left: title + timestamp */}
      <div style={{ minWidth: 110, flexShrink: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
          {icon} {title}
        </div>
        {collectedAt && (
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
            {dayjs(collectedAt).format("MM-DD HH:mm")}
          </div>
        )}
      </div>

      {/* Center: metrics */}
      <div style={{ flex: 1, display: "flex", flexWrap: "wrap", gap: "4px 20px", alignItems: "center" }}>
        {noData
          ? <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无数据</span>
          : children}
      </div>

      {/* Right: buttons */}
      <div style={{ flexShrink: 0, display: "flex", gap: 4, alignItems: "center" }}>
        {onRefresh && (
          refreshDisabled ? (
            <Tooltip title={refreshDisabledTip}>
              <Button size="small" icon={<ReloadOutlined />} disabled style={{ fontSize: 11 }} />
            </Tooltip>
          ) : (
            <Button
              size="small"
              icon={<ReloadOutlined spin={refreshing} />}
              onClick={onRefresh}
              loading={refreshing}
              style={{ fontSize: 11 }}
            >
              {noData ? "获取" : "刷新"}
            </Button>
          )
        )}
        {onViewRaw && !noData && (
          <Button size="small" icon={<CodeOutlined />} onClick={onViewRaw} style={{ fontSize: 11 }}>
            原始
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Per-source metrics ───────────────────────────────────────────────────────

/** 从 raw_data.sportmonks 中提取概率预测（兼容新旧两种数据结构） */
function extractSportmonksPreds(data: Record<string, unknown>) {
  // 新格式: predictions 在顶层；旧格式: 在 fixture.predictions 内
  const fixture = data.fixture as Record<string, unknown> | undefined;
  const preds = (
    (data.predictions as Array<Record<string, unknown>> | undefined) ??
    (fixture?.predictions as Array<Record<string, unknown>> | undefined)
  );
  if (!preds?.length) return null;

  const result: {
    fulltime?: { home: number; draw: number; away: number };
    btts_yes?: number;
    over25_yes?: number;
  } = {};

  for (const p of preds) {
    const devName = (p.type as Record<string, unknown> | undefined)?.developer_name as string | undefined;
    const vals = p.predictions as Record<string, number> | undefined;
    if (!vals) continue;
    if (devName === "FULLTIME_RESULT_PROBABILITY") {
      result.fulltime = { home: vals.home, draw: vals.draw, away: vals.away };
    } else if (devName === "BTTS_PROBABILITY") {
      result.btts_yes = vals.yes;
    } else if (devName === "OVER_UNDER_2_5_PROBABILITY") {
      result.over25_yes = vals.yes;
    }
  }
  return Object.keys(result).length > 0 ? result : null;
}

function SportmonksMetrics({ data, homeTeam, awayTeam }: {
  data: Record<string, unknown>; homeTeam: string; awayTeam: string;
}) {
  const fixture = data.fixture as Record<string, unknown> | undefined;

  // Lineup count
  const lineups = (fixture?.lineups ?? data.lineups) as Array<Record<string, unknown>> | undefined;
  let lineupInfo: string | null = null;
  if (lineups?.length) {
    const homeId = fixture?.home_id;
    const awayId = fixture?.away_id;
    const homeCount = homeId ? lineups.filter((l) => l.team_id === homeId).length : Math.floor(lineups.length / 2);
    const awayCount = awayId ? lineups.filter((l) => l.team_id === awayId).length : lineups.length - homeCount;
    lineupInfo = `${homeTeam || "主"} ${homeCount}人 | ${awayTeam || "客"} ${awayCount}人`;
  }

  const preds = extractSportmonksPreds(data);

  if (!preds && !lineupInfo) {
    return <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无数据</span>;
  }

  return (
    <>
      {preds?.fulltime && (
        <MetricItem
          label="胜平负"
          value={`主 ${preds.fulltime.home.toFixed(1)}% | 平 ${preds.fulltime.draw.toFixed(1)}% | 客 ${preds.fulltime.away.toFixed(1)}%`}
        />
      )}
      {preds?.btts_yes != null && (
        <MetricItem label="BTTS" value={`${preds.btts_yes.toFixed(1)}%`} />
      )}
      {preds?.over25_yes != null && (
        <MetricItem label="大2.5" value={`${preds.over25_yes.toFixed(1)}%`} />
      )}
      {lineupInfo && <MetricItem label="阵容" value={lineupInfo} />}
    </>
  );
}

function OddalertsMetrics({ data, homeTeam, awayTeam }: {
  data: Record<string, unknown>; homeTeam: string; awayTeam: string;
}) {
  const oddsHistory = data.odds_history as { data: unknown[] } | undefined;
  const statsData = data.stats as { data: Array<Record<string, unknown>> } | undefined;
  const fixtureData = data.fixture as Record<string, unknown> | undefined;
  const homeId = fixtureData?.home_id;
  const awayId = fixtureData?.away_id;

  const oddsRows = oddsHistory?.data as Array<Record<string, unknown>> | undefined;
  const ftOdds = oddsRows?.length ? extractFtOdds(oddsRows) : null;

  let homeXg: number | null = null;
  let awayXg: number | null = null;
  if (statsData?.data?.length) {
    const hs = homeId ? statsData.data.find((t) => t.team_id === homeId) : statsData.data[0];
    const as_ = awayId ? statsData.data.find((t) => t.team_id === awayId) : statsData.data[1];
    if (hs?.xg_for != null) { const v = Number(hs.xg_for); if (!isNaN(v)) homeXg = v; }
    if (as_?.xg_for != null) { const v = Number(as_.xg_for); if (!isNaN(v)) awayXg = v; }
  }

  const probability = (fixtureData?.probability ?? data.probability) as Record<string, number> | undefined;

  const hasContent = ftOdds || homeXg != null || awayXg != null || probability;
  if (!hasContent) {
    const hasEmptyOdds = oddsRows != null && oddsRows.length === 0;
    return (
      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
        {hasEmptyOdds ? "暂无赔率数据（fixture_id 可能不匹配）" : "暂无数据"}
      </span>
    );
  }

  return (
    <>
      {ftOdds && (
        <MetricItem
          label={`${ftOdds.bookmaker} 收`}
          value={[
            ftOdds.home ? `主 ${ftOdds.home.closing.toFixed(2)}` : "",
            ftOdds.draw ? `平 ${ftOdds.draw.closing.toFixed(2)}` : "",
            ftOdds.away ? `客 ${ftOdds.away.closing.toFixed(2)}` : "",
          ].filter(Boolean).join(" | ")}
        />
      )}
      {ftOdds?.home && ftOdds.home.opening !== ftOdds.home.closing && (
        <MetricItem
          label="开盘"
          value={[
            ftOdds.home ? `主 ${ftOdds.home.opening.toFixed(2)}` : "",
            ftOdds.draw ? `平 ${ftOdds.draw.opening.toFixed(2)}` : "",
            ftOdds.away ? `客 ${ftOdds.away.opening.toFixed(2)}` : "",
          ].filter(Boolean).join(" | ")}
        />
      )}
      {(homeXg != null || awayXg != null) && (
        <MetricItem
          label="xG"
          value={`${homeTeam || "主"} ${fmt(homeXg)} | ${awayTeam || "客"} ${fmt(awayXg)}`}
        />
      )}
      {probability && (
        <MetricItem
          label="模型概率"
          value={`主 ${fmtPct(probability.home_win)} | 平 ${fmtPct(probability.draw)} | 客 ${fmtPct(probability.away_win)}`}
        />
      )}
    </>
  );
}

// ─── MatchDataPanel ───────────────────────────────────────────────────────────

const KNOWN_SOURCES = ["oddalerts"];
const SOURCE_CAN_REFRESH = new Set(["oddalerts"]);
const SOURCE_LABELS: Record<string, string> = {
  sportmonks: "SportMonks",
  oddalerts: "OddAlerts",
  footystats: "FootyStats",
};
const SOURCE_ICONS: Record<string, string> = {
  sportmonks: "⚽",
  oddalerts: "📈",
  footystats: "📊",
};

interface MatchDataPanelProps {
  record: JsonRecord;
  onViewRaw: (title: string, data: unknown) => void;
  onRefresh: (matchId: string, source: string) => Promise<void>;
  refreshingSource: string | null;
}

function MatchDataPanel({ record, onViewRaw, onRefresh, refreshingSource }: MatchDataPanelProps) {
  const matchId = record.match_id as string | undefined;
  const rawData = record.raw_data as Record<string, Record<string, unknown>> | undefined;
  const analysis = record.analysis as Record<string, unknown> | undefined;
  const homeTeam = (record.home_team as string) ?? "";
  const awayTeam = (record.away_team as string) ?? "";

  const existingSources = rawData ? Object.keys(rawData) : [];
  const missingSources = KNOWN_SOURCES.filter((s) => !existingSources.includes(s));

  return (
    <div style={{
      padding: "10px 16px 14px",
      background: "color-mix(in srgb, var(--nav-bg) 60%, var(--card-bg) 40%)",
      borderBottom: "2px solid var(--border)",
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>

        {/* Analysis */}
        {analysis && (() => {
          const src = flattenAnalysis(analysis);
          const probs = src.fulltime_result_probabilities as Record<string, number> | undefined;
          const ah = src.ah_recommendation as Record<string, unknown> | undefined;
          const ahStr = ah ? `${ah.side || ""} ${ah.line ?? ""}`.trim() : undefined;
          return (
            <SourceCard
              key="analysis"
              title="分析结果"
              icon="🤖"
              onViewRaw={() => onViewRaw("分析结果 (analysis)", analysis)}
            >
              {(src.home_xg != null || src.away_xg != null) && (
                <MetricItem label="xG" value={`${homeTeam || "主"} ${fmt(src.home_xg)} | ${awayTeam || "客"} ${fmt(src.away_xg)}`} />
              )}
              {probs && (
                <MetricItem
                  label="概率"
                  value={`主 ${fmtPct(probs.home_win ?? probs.home)} | 平 ${fmtPct(probs.draw)} | 客 ${fmtPct(probs.away_win ?? probs.away)}`}
                />
              )}
              {ahStr && <MetricItem label="推荐" value={ahStr} highlight />}
              {src.confidence != null && <MetricItem label="置信度" value={`${src.confidence}%`} />}
            </SourceCard>
          );
        })()}

        {/* Existing sources */}
        {existingSources.map((source) => {
          const data = rawData![source];
          const meta = data._meta as Record<string, unknown> | undefined;
          return (
            <SourceCard
              key={source}
              title={SOURCE_LABELS[source] ?? source}
              icon={SOURCE_ICONS[source] ?? "🔌"}
              collectedAt={meta?.collected_at as string | undefined}
              onViewRaw={() => onViewRaw(`${SOURCE_LABELS[source] ?? source} (raw_data.${source})`, data)}
              onRefresh={matchId ? () => onRefresh(matchId, source) : undefined}
              refreshing={refreshingSource === source}
              refreshDisabled={!SOURCE_CAN_REFRESH.has(source)}
              refreshDisabledTip={`${SOURCE_LABELS[source] ?? source} 数据通过流水线自动更新`}
            >
              {source === "sportmonks" && <SportmonksMetrics data={data} homeTeam={homeTeam} awayTeam={awayTeam} />}
              {source === "oddalerts" && <OddalertsMetrics data={data} homeTeam={homeTeam} awayTeam={awayTeam} />}
            </SourceCard>
          );
        })}

        {/* Missing known sources */}
        {missingSources.map((source) => (
          <SourceCard
            key={source}
            title={SOURCE_LABELS[source]}
            icon={SOURCE_ICONS[source]}
            noData
            onRefresh={matchId ? () => onRefresh(matchId, source) : undefined}
            refreshing={refreshingSource === source}
          />
        ))}
      </div>
    </div>
  );
}

// ─── Main BoardPage ───────────────────────────────────────────────────────────

export default function BoardPage() {
  const config = useConfig();
  const tabs = config.board.tabs;
  const [activeDir, setActiveDir] = useState(tabs[0]?.dir ?? "");
  const [items, setItems] = useState<JsonRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Inline expansion
  const [expandedRowKey, setExpandedRowKey] = useState<string | null>(null);
  const [expandedRecord, setExpandedRecord] = useState<JsonRecord | null>(null);

  // Raw JSON drawer
  const [rawDrawer, setRawDrawer] = useState<{ title: string; data: unknown } | null>(null);

  // Per-source refresh
  const [refreshingSource, setRefreshingSource] = useState<string | null>(null);

  const boardRefreshDirs = useAppStore((s) => s.boardRefreshDirs);
  const consumeBoardRefresh = useAppStore((s) => s.consumeBoardRefresh);
  const injectChatMessage = useAppStore((s) => s.injectChatMessage);

  const PAGE_SIZE = 20;

  const fetchList = useCallback(
    async (dir: string, p: number, source?: BoardTabSource) => {
      setLoading(true);
      try {
        if (source && source.provider === "rest" && source.endpoints?.list) {
          const res = await api.getBoardListCustom(source.endpoints.list, { page: p, page_size: PAGE_SIZE });
          const mapping = source.list_response ?? {};
          setItems((res as Record<string, unknown>)[mapping.items ?? "items"] as JsonRecord[] ?? []);
          setTotal((res as Record<string, unknown>)[mapping.total ?? "total"] as number ?? 0);
        } else {
          const res = await api.getBoardList(dir, { page: p, page_size: PAGE_SIZE });
          setItems(res.items);
          setTotal(res.total);
        }
      } catch {
        setItems([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (activeDir) {
      const tab = tabs.find((t) => t.dir === activeDir);
      fetchList(activeDir, page, tab?.source);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeDir, page, fetchList]);

  useEffect(() => {
    if (boardRefreshDirs.includes(activeDir)) {
      const tab = tabs.find((t) => t.dir === activeDir);
      fetchList(activeDir, page, tab?.source);
      consumeBoardRefresh(activeDir);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boardRefreshDirs, activeDir, page, fetchList, consumeBoardRefresh]);

  const handleTabChange = (dir: string) => {
    setActiveDir(dir);
    setPage(1);
    setItems([]);
    setSortKey(null);
    setSortOrder("asc");
    setExpandedRowKey(null);
    setExpandedRecord(null);
  };

  const handleSort = (colKey: string) => {
    if (sortKey === colKey) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortKey(colKey);
      setSortOrder("asc");
    }
  };

  const sortedItems = [...items].sort((a, b) => {
    if (!sortKey) return 0;
    const aVal = a[sortKey], bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return sortOrder === "asc" ? -1 : 1;
    if (bVal == null) return sortOrder === "asc" ? 1 : -1;
    const cmp = typeof aVal === "number" && typeof bVal === "number"
      ? aVal - bVal
      : String(aVal).localeCompare(String(bVal));
    return sortOrder === "asc" ? cmp : -cmp;
  });

  const getRowKey = (record: JsonRecord, i: number): string => {
    const tab = tabs.find((t) => t.dir === activeDir);
    return tab?.source ? String(record[tab.source.id_field] ?? i) : record._filename;
  };

  const handleRowToggle = (record: JsonRecord, rowKey: string) => {
    if (expandedRowKey === rowKey) {
      setExpandedRowKey(null);
      setExpandedRecord(null);
    } else {
      setExpandedRowKey(rowKey);
      setExpandedRecord(record);
    }
  };

  const handleRefreshSource = async (matchId: string, source: string) => {
    setRefreshingSource(source);
    try {
      const result = await api.refreshMatchSource(matchId, source);
      if (expandedRecord) {
        const updated = {
          ...expandedRecord,
          raw_data: {
            ...(expandedRecord.raw_data as Record<string, unknown> ?? {}),
            [source]: result.data,
          },
        };
        setExpandedRecord(updated);
        // Also update items array so the data persists after collapse/re-expand
        setItems((prev) => prev.map((item) =>
          (item.match_id === matchId ? updated : item) as JsonRecord
        ));
      }
      message.success(`${source} 数据已更新`);
    } catch (e) {
      message.error(`获取失败: ${e instanceof Error ? e.message : "未知错误"}`);
    } finally {
      setRefreshingSource(null);
    }
  };

  const handleViewRaw = (title: string, data: unknown) => {
    setRawDrawer({ title, data });
  };

  const handleInjectChat = (record: JsonRecord) => {
    const tab = tabs.find((t) => t.dir === activeDir);
    if (tab?.source) {
      const idValue = String(record[tab.source.id_field] ?? "unknown");
      injectChatMessage(`请解读以下数据（${idValue}）：\n\n${JSON.stringify(record, null, 2)}`);
    } else {
      const { _filename, ...rest } = record;
      injectChatMessage(`请解读以下数据（${_filename}）：\n\n${JSON.stringify(rest, null, 2)}`);
    }
  };

  const activeTab = tabs.find((t) => t.dir === activeDir);
  const colCount = activeTab?.columns.length ?? 1;

  // Detect whether inline panel should use match-specific layout
  const isMatchRecord = (record: JsonRecord) =>
    typeof record.match_id === "string" && typeof record.raw_data === "object";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Tabs
        activeKey={activeDir}
        onChange={handleTabChange}
        items={tabs.map((t: BoardTab) => ({ key: t.dir, label: t.label }))}
      />

      {loading ? (
        <div style={{ padding: 40, textAlign: "center" }}><Spin /></div>
      ) : items.length === 0 ? (
        <Empty description="暂无数据" style={{ padding: 40 }} />
      ) : (
        <div style={{
          background: "var(--card-bg)", border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)", overflow: "hidden",
        }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "var(--nav-bg)" }}>
                {activeTab?.columns.map((col) => {
                  const isSorted = sortKey === col.key;
                  return (
                    <th
                      key={col.key}
                      onClick={() => handleSort(col.key)}
                      style={{
                        padding: "8px 16px", textAlign: "left",
                        fontSize: 11, fontWeight: 600,
                        color: isSorted ? "var(--accent)" : "var(--text-muted)",
                        textTransform: "uppercase", letterSpacing: "0.06em",
                        borderBottom: "1px solid var(--border)",
                        cursor: "pointer", userSelect: "none",
                      }}
                    >
                      {col.label}{isSorted ? (sortOrder === "asc" ? " ↑" : " ↓") : ""}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((record, i) => {
                const rowKey = getRowKey(record, i);
                const isExpanded = expandedRowKey === rowKey;

                return (
                  <Fragment key={rowKey}>
                    {/* Data row */}
                    <tr
                      style={{
                        borderBottom: isExpanded ? "none" : "1px solid var(--border-subtle)",
                        background: isExpanded ? "color-mix(in srgb, var(--nav-bg) 40%, transparent)" : "transparent",
                        cursor: "pointer",
                      }}
                      onClick={() => handleRowToggle(record, rowKey)}
                      onMouseEnter={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "var(--hover-bg)";
                      }}
                      onMouseLeave={(e) => {
                        if (!isExpanded) (e.currentTarget as HTMLElement).style.background = "transparent";
                      }}
                    >
                      {activeTab?.columns.map((col, colIdx) => (
                        <td key={col.key} style={{ padding: "10px 16px", color: "var(--text-secondary)" }}>
                          {colIdx === 0 ? (
                            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ color: "var(--text-muted)", fontSize: 10, flexShrink: 0 }}>
                                {isExpanded ? <DownOutlined /> : <RightOutlined />}
                              </span>
                              <span style={{ color: "var(--accent)", fontFamily: "var(--font-mono)", fontSize: 12 }}>
                                <CellRenderer col={col} value={record[col.key]} />
                              </span>
                            </span>
                          ) : (
                            <CellRenderer col={col} value={record[col.key]} />
                          )}
                        </td>
                      ))}
                    </tr>

                    {/* Expanded detail row */}
                    {isExpanded && (
                      <tr>
                        <td colSpan={colCount} style={{ padding: 0, borderBottom: "1px solid var(--border)" }}>
                          {expandedRecord && isMatchRecord(expandedRecord) ? (
                            <MatchDataPanel
                              record={expandedRecord}
                              onViewRaw={handleViewRaw}
                              onRefresh={handleRefreshSource}
                              refreshingSource={refreshingSource}
                            />
                          ) : expandedRecord ? (
                            (() => {
                              if (activeTab?.source?.detail.mode === "tabs" && activeTab.source.detail.tabs?.length) {
                                return (
                                  <div style={{ padding: "8px 16px" }}>
                                    <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginBottom: 8 }}>
                                      <Button size="small" onClick={() => handleInjectChat(expandedRecord)}>助手解读</Button>
                                    </div>
                                    <Tabs
                                      size="small"
                                      items={activeTab.source.detail.tabs!.map((dt) => ({
                                        key: dt.label,
                                        label: dt.label,
                                        children: <DetailTabRenderer tab={dt} data={expandedRecord} />,
                                      }))}
                                    />
                                  </div>
                                );
                              }
                              return (
                                <div style={{ padding: 16 }}>
                                  <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginBottom: 8 }}>
                                    <Button size="small" onClick={() => handleViewRaw("原始数据", expandedRecord)}>查看原始数据</Button>
                                    <Button size="small" type="primary" onClick={() => handleInjectChat(expandedRecord)}>助手解读</Button>
                                  </div>
                                  <pre style={{
                                    background: "#0a0a12", color: "var(--green)",
                                    padding: 12, borderRadius: 6, fontSize: 12,
                                    overflowX: "auto", whiteSpace: "pre-wrap",
                                    border: "1px solid var(--border)", maxHeight: 300, overflow: "auto",
                                  }}>
                                    {JSON.stringify(
                                      Object.fromEntries(Object.entries(expandedRecord).filter(([k]) => k !== "_filename")),
                                      null, 2,
                                    )}
                                  </pre>
                                </div>
                              );
                            })()
                          ) : null}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>

          {total > PAGE_SIZE && (
            <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)", textAlign: "right" }}>
              <Pagination
                current={page}
                total={total}
                pageSize={PAGE_SIZE}
                onChange={setPage}
                size="small"
                showTotal={(t) => `共 ${t} 条`}
              />
            </div>
          )}
        </div>
      )}

      {/* Raw JSON Drawer */}
      <Drawer
        title={rawDrawer?.title ?? "原始数据"}
        placement="right"
        width={580}
        onClose={() => setRawDrawer(null)}
        open={!!rawDrawer}
      >
        <pre style={{
          background: "#0a0a12", color: "var(--green)",
          padding: 16, borderRadius: 8, fontSize: 12,
          overflowX: "auto", whiteSpace: "pre-wrap",
          border: "1px solid var(--border)",
        }}>
          {rawDrawer ? JSON.stringify(rawDrawer.data, null, 2) : ""}
        </pre>
      </Drawer>
    </div>
  );
}
