import { type ReactNode } from "react";
import { Button, Tooltip } from "antd";
import { ReloadOutlined, CodeOutlined } from "@ant-design/icons";
import dayjs from "dayjs";

// ─── Utilities ────────────────────────────────────────────────────────────────

function fmt(n: unknown, d = 2): string {
  const v = Number(n);
  return isNaN(v) ? "—" : v.toFixed(d);
}

function fmtPct(n: unknown): string {
  const v = Number(n);
  if (isNaN(v)) return "—";
  return (v > 1 ? v : v * 100).toFixed(1) + "%";
}

// ─── Types ────────────────────────────────────────────────────────────────────

interface FtOdds {
  bookmaker: string;
  home?: { opening: number; closing: number };
  draw?: { opening: number; closing: number };
  away?: { opening: number; closing: number };
}

// ─── Shared extractors ────────────────────────────────────────────────────────

export function extractFtOdds(rows: Array<Record<string, unknown>>): FtOdds | null {
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

export function extractSportmonksPreds(data: Record<string, unknown>) {
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

// ─── MetricItem ───────────────────────────────────────────────────────────────

export function MetricItem({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
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

// ─── SourceCard ───────────────────────────────────────────────────────────────

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

export function SourceCard({
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

      <div style={{ flex: 1, display: "flex", flexWrap: "wrap", gap: "4px 20px", alignItems: "center" }}>
        {noData
          ? <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无数据</span>
          : children}
      </div>

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

export function SportmonksMetrics({ data, homeTeam, awayTeam }: {
  data: Record<string, unknown>; homeTeam: string; awayTeam: string;
}) {
  const fixture = data.fixture as Record<string, unknown> | undefined;
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

export function OddalertsMetrics({ data, homeTeam, awayTeam }: {
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

// ─── Constants ────────────────────────────────────────────────────────────────

export const KNOWN_SOURCES = ["oddalerts"];
export const SOURCE_CAN_REFRESH = new Set(["oddalerts"]);
export const SOURCE_LABELS: Record<string, string> = {
  sportmonks: "SportMonks",
  oddalerts: "OddAlerts",
  footystats: "FootyStats",
};
export const SOURCE_ICONS: Record<string, string> = {
  sportmonks: "⚽",
  oddalerts: "📈",
  footystats: "📊",
};

// ─── MatchDataPanel ───────────────────────────────────────────────────────────

export interface MatchDataPanelProps {
  record: Record<string, unknown>;
  onViewRaw: (title: string, data: unknown) => void;
  onRefresh: (matchId: string, source: string) => Promise<void>;
  refreshingSource: string | null;
}

export function MatchDataPanel({ record, onViewRaw, onRefresh, refreshingSource }: MatchDataPanelProps) {
  const matchId = record.match_id as string | undefined;
  const rawData = record.raw_data as Record<string, Record<string, unknown>> | undefined;
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

// ─── LoadingMatchPanel ────────────────────────────────────────────────────────

export function LoadingMatchPanel() {
  return (
    <div style={{
      padding: "16px",
      background: "color-mix(in srgb, var(--nav-bg) 60%, var(--card-bg) 40%)",
      borderBottom: "2px solid var(--border)",
      color: "var(--text-muted)", fontSize: 12, textAlign: "center",
    }}>
      加载数据源...
    </div>
  );
}

// ─── AnalysisMetrics (from pipeline analysis field) ──────────────────────────

export function AnalysisMetrics({ record }: { record: Record<string, unknown> }) {
  const homeXg = record.home_xg as number | undefined;
  const awayXg = record.away_xg as number | undefined;
  const probs = record.result_probs as { home_win: number; draw: number; away_win: number } | undefined;
  const rec = record.recommendation as string | undefined;
  const ev = record.ev as number | undefined;
  const confidence = record.confidence as number | undefined;

  const hasAny = homeXg != null || awayXg != null || probs || rec || ev != null || confidence != null;
  if (!hasAny) return <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无分析数据</span>;

  return (
    <>
      {(homeXg != null || awayXg != null) && (
        <MetricItem label="xG" value={`主 ${fmt(homeXg)} | 客 ${fmt(awayXg)}`} highlight />
      )}
      {probs && (
        <MetricItem
          label="胜平负"
          value={`主 ${fmtPct(probs.home_win)} | 平 ${fmtPct(probs.draw)} | 客 ${fmtPct(probs.away_win)}`}
        />
      )}
      {rec && <MetricItem label="推荐" value={rec} highlight />}
      {ev != null && (
        <MetricItem label="EV" value={`${ev >= 0 ? "+" : ""}${ev.toFixed(3)}`} highlight={ev > 0.05} />
      )}
      {confidence != null && (
        <MetricItem label="置信度" value={`${(confidence * 100).toFixed(1)}%`} />
      )}
    </>
  );
}

// ─── PipelineMatchPanel ───────────────────────────────────────────────────────

interface PipelineMatchPanelProps {
  matchId: string;
  pipelineSummary: Record<string, unknown>;
  onViewRaw: (title: string, data: unknown) => void;
  onRefresh: (matchId: string, source: string) => Promise<void>;
  refreshingSource: string | null;
  fullRecord: Record<string, unknown> | null;
  loading: boolean;
}

export function PipelineMatchPanel({
  matchId, pipelineSummary, onViewRaw, onRefresh, refreshingSource, fullRecord, loading,
}: PipelineMatchPanelProps) {
  const homeTeam = (pipelineSummary.home_team as string) ?? "";
  const awayTeam = (pipelineSummary.away_team as string) ?? "";

  if (loading) return <LoadingMatchPanel />;

  const rawData = fullRecord?.raw_data as Record<string, Record<string, unknown>> | undefined;
  const existingSources = rawData ? Object.keys(rawData) : [];
  const missingSources = KNOWN_SOURCES.filter((s) => !existingSources.includes(s));

  return (
    <div style={{
      padding: "10px 16px 14px",
      background: "color-mix(in srgb, var(--nav-bg) 60%, var(--card-bg) 40%)",
      borderBottom: "2px solid var(--border)",
      display: "flex", flexDirection: "column", gap: 6,
    }}>
      {/* Analysis summary from pipeline */}
      <SourceCard
        title="流水线分析"
        icon="🧠"
      >
        <AnalysisMetrics record={pipelineSummary} />
      </SourceCard>

      {/* Raw data sources */}
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
  );
}

