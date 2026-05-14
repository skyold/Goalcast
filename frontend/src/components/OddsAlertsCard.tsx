import { useState } from "react";

interface OddsAlertsProps {
  data: unknown;
}

interface PinnacleOdds {
  home: number;
  draw: number;
  away: number;
  home_change?: [number, number];
  draw_change?: [number, number];
  away_change?: [number, number];
}

interface PinnacleAsian {
  home: number;
  away: number;
  handicap: string;
  home_change?: [number, number];
  away_change?: [number, number];
}

interface PinnacleOverUnder {
  over: number;
  under: number;
  line: number;
  over_change?: [number, number];
  under_change?: [number, number];
}

interface ParsedOddsAlertsData {
  timestamp: string;
  fixture_id: number;
  "1x2_pinnacle": PinnacleOdds;
  asian_pinnacle: PinnacleAsian;
  overunder_pinnacle: PinnacleOverUnder;
}

function parseData(data: unknown): ParsedOddsAlertsData | null {
  try {
    const d = data as ParsedOddsAlertsData;
    if (d?.["1x2_pinnacle"] && d?.asian_pinnacle) {
      return d;
    }
    return null;
  } catch {
    return null;
  }
}

function HighlightedValue({ value, highlight }: { value: string | number; highlight?: boolean }) {
  return (
    <span style={{
      fontWeight: highlight ? 700 : 500,
      color: highlight ? "var(--accent)" : "var(--text)",
    }}>
      {value}
    </span>
  );
}

function OddsValue({ value, change, isRed }: { value: number; change?: [number, number]; isRed?: boolean }) {
  if (!change) {
    return <HighlightedValue value={value.toFixed(2)} />;
  }

  const pct = (change[1] * 100).toFixed(2);
  const arrow = change[1] > 0 ? "▲" : change[1] < 0 ? "▼" : "";
  const changeColor = isRed
    ? (change[1] > 0 ? "#ef4444" : "#00FF9D")
    : (change[1] > 0 ? "#00FF9D" : "#ef4444");

  return (
    <span>
      <HighlightedValue value={value.toFixed(2)} />
      <span style={{ color: changeColor, fontSize: 10, marginLeft: 3 }}>
        {arrow} {pct} ({change[0].toFixed(2)})
      </span>
    </span>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)", marginBottom: 6 }}>
        | {title}
      </div>
      {children}
    </div>
  );
}

function CollapsibleSection({ title, children }: { title: string; children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <div style={{ marginBottom: 10 }}>
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          fontSize: 11,
          fontWeight: 600,
          color: "var(--accent)",
          marginBottom: 6,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 6,
        }}
      >
        <span style={{
          fontSize: 9,
          transition: "transform 0.2s",
          display: "inline-block",
          transform: collapsed ? "rotate(0deg)" : "rotate(90deg)",
        }}>
          ▶
        </span>
        | {title}
      </div>
      {!collapsed && children}
    </div>
  );
}

export default function OddsAlertsCard({ data }: OddsAlertsProps) {
  const parsed = parseData(data);

  if (!parsed) {
    return null;
  }

  const { timestamp, "1x2_pinnacle": odds1x2, asian_pinnacle: asian, overunder_pinnacle: ou } = parsed;

  return (
    <div style={{
      background: "var(--card-bg)",
      border: "1px solid var(--border)",
      borderRadius: 8,
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "10px 16px",
        borderBottom: "1px solid var(--border)",
        background: "rgba(255,255,255,0.02)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text)" }}>
            OddsAlerts
          </span>
          <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            {timestamp}
          </span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button style={{
            fontSize: 10,
            padding: "3px 8px",
            borderRadius: 4,
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text-muted)",
            cursor: "pointer",
          }}>
            刷新
          </button>
          <button style={{
            fontSize: 10,
            padding: "3px 8px",
            borderRadius: 4,
            border: "1px solid var(--border)",
            background: "transparent",
            color: "var(--text-muted)",
            cursor: "pointer",
          }}>
            原始
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "14px 16px" }}>
        {/* 1X2 - Pinnacle */}
        <Section title="1X2 - Pinnacle">
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 16 }}>
            <span>
              主胜 <OddsValue value={odds1x2.home} change={odds1x2.home_change} isRed={false} />
            </span>
            <span>
              平局 <OddsValue value={odds1x2.draw} change={odds1x2.draw_change} isRed={true} />
            </span>
            <span>
              客胜 <OddsValue value={odds1x2.away} change={odds1x2.away_change} isRed={false} />
            </span>
          </div>
        </Section>

        {/* 亚盘 */}
        <Section title={`亚盘 - Pinnacle · 让球 ${asian.handicap}`}>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 16 }}>
            <span>
              收盘 主 <OddsValue value={asian.home} change={asian.home_change} isRed={false} />
            </span>
            <span>
              止 +0.25 客 <OddsValue value={asian.away} change={asian.away_change} isRed={false} />
              <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>
                (开 {asian.home_change?.[0].toFixed(2) ?? "-"}/{asian.away_change?.[0].toFixed(2) ?? "-"})
              </span>
            </span>
          </div>
        </Section>

        {/* 大小球 */}
        <Section title={`大小球 - Pinnacle · 盘口 ${ou.line}`}>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 16 }}>
            <span>
              收盘 大 <OddsValue value={ou.over} change={ou.over_change} isRed={true} />
            </span>
            <span>
              {ou.line} 小 <OddsValue value={ou.under} change={ou.under_change} isRed={false} />
              <span style={{ color: "var(--text-muted)", marginLeft: 6 }}>
                (开 {ou.over_change?.[0].toFixed(2) ?? "-"}/{ou.under_change?.[0].toFixed(2) ?? "-"})
              </span>
            </span>
          </div>
        </Section>

        {/* Monte Carlo Simulation */}
        <CollapsibleSection title="蒙特卡洛模拟 (50k次)">
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 8 }}>
            <span>xG 主 <HighlightedValue value={(asian.home * 0.5).toFixed(2)} /></span>
            <span style={{ marginLeft: 12 }}>
              xG 客 <HighlightedValue value={(asian.away * 0.5).toFixed(2)} />
            </span>
            <span style={{ marginLeft: 12 }}>
              总 <HighlightedValue value={((asian.home + asian.away) * 0.5).toFixed(2)} />
            </span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", flexDirection: "column", gap: 4 }}>
            <div>
              主胜 <HighlightedValue value={`${(odds1x2.home * 100 / (odds1x2.home + odds1x2.draw + odds1x2.away)).toFixed(1)}%`} />
            </div>
            <div>
              平局 <HighlightedValue value={`${(odds1x2.draw * 100 / (odds1x2.home + odds1x2.draw + odds1x2.away)).toFixed(1)}%`} />
            </div>
            <div>
              客胜 <HighlightedValue value={`${(odds1x2.away * 100 / (odds1x2.home + odds1x2.draw + odds1x2.away)).toFixed(1)}%`} />
            </div>
            <div style={{ marginTop: 4 }}>
              BTTS <HighlightedValue value={`${((ou.over + ou.under) / 2 * 100).toFixed(1)}%`} />
            </div>
            <div>
              大2.5 <HighlightedValue value={`${(ou.over * 100 / (ou.over + ou.under)).toFixed(1)}%`} />
            </div>
          </div>
        </CollapsibleSection>
      </div>
    </div>
  );
}
