import { useState } from "react";

interface SportMonksProps {
  data: unknown;
}

interface Probabilities1x2 {
  home: number;
  draw: number;
  away: number;
}

interface XGData {
  home: number;
  away: number;
  total: number;
}

interface HalfTime1x2 {
  home: number;
  draw: number;
  away: number;
}

interface ParsedSportMonksData {
  timestamp: string;
  fixture_id: number;
  probabilities_1x2: Probabilities1x2;
  xg: XGData;
  btts: number;
  over_2_5: number;
  over_1_5: number;
  correct_score: Record<string, number>;
  half_time_1x2: HalfTime1x2;
  monte_carlo?: {
    xg_home: number;
    xg_away: number;
    xg_total: number;
    simulations: number;
    probabilities_1x2: Probabilities1x2;
    btts: number;
    over_2_5: number;
    half_time_1x2: HalfTime1x2;
    correct_score: Record<string, number>;
  };
}

function parseData(data: unknown): ParsedSportMonksData | null {
  try {
    const d = data as ParsedSportMonksData;
    if (d?.probabilities_1x2 && d?.xg) {
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

export default function SportMonksCard({ data }: SportMonksProps) {
  const parsed = parseData(data);

  if (!parsed) {
    return null;
  }

  const { probabilities_1x2: p1x2, xg, btts, over_2_5, over_1_5, correct_score, half_time_1x2: ht1x2, timestamp, monte_carlo } = parsed;

  const homeWin = p1x2.home;
  const draw = p1x2.draw;
  const awayWin = p1x2.away;

  const maxProb = Math.max(homeWin, draw, awayWin);

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
            SportMonks
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
        {/* 全场胜平负赔率 */}
        <Section title="全场胜平负赔率">
          <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6 }}>
            <span>主胜 <HighlightedValue value={`${(homeWin * 100).toFixed(1)}%`} highlight={homeWin === maxProb} /></span>
            <span style={{ marginLeft: 12 }}>
              平 <HighlightedValue value={`${(draw * 100).toFixed(1)}%`} highlight={draw === maxProb} />
            </span>
            <span style={{ marginLeft: 12 }}>
              客胜 <HighlightedValue value={`${(awayWin * 100).toFixed(1)}%`} highlight={awayWin === maxProb} />
            </span>
          </div>
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 16 }}>
            <span>
              xG 主 <HighlightedValue value={xg.home.toFixed(2)} />
            </span>
            <span>
              xG 客 <HighlightedValue value={xg.away.toFixed(2)} />
            </span>
            <span>
              BTTS <HighlightedValue value={`${(btts * 100).toFixed(1)}%`} />
            </span>
            <span>
              大2.5 <HighlightedValue value={`${(over_2_5 * 100).toFixed(1)}%`} />
            </span>
            <span>
              大1.5 <HighlightedValue value={`${(over_1_5 * 100).toFixed(1)}%`} />
            </span>
          </div>
        </Section>

        {/* 半场胜平负 */}
        <Section title="半场胜平负">
          <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
            <span>主胜 <HighlightedValue value={`${(ht1x2.home * 100).toFixed(1)}%`} /></span>
            <span style={{ marginLeft: 12 }}>
              平 <HighlightedValue value={`${(ht1x2.draw * 100).toFixed(1)}%`} />
            </span>
            <span style={{ marginLeft: 12 }}>
              客胜 <HighlightedValue value={`${(ht1x2.away * 100).toFixed(1)}%`} />
            </span>
          </div>
        </Section>

        {/* 正确比分概率 */}
        <CollapsibleSection title="正确比分概率">
          <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 10, flexWrap: "wrap" }}>
            {Object.entries(correct_score)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 6)
              .map(([score, prob]) => (
                <span key={score}>
                  {score} <HighlightedValue value={`${(prob * 100).toFixed(1)}%`} />
                </span>
              ))}
          </div>
        </CollapsibleSection>

        {/* Monte Carlo (if available) */}
        {monte_carlo && (
          <>
            <Section title={`蒙特卡洛模拟 (${monte_carlo.simulations}次)`}>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6 }}>
                <span>xG 主 <HighlightedValue value={monte_carlo.xg_home.toFixed(2)} /></span>
                <span style={{ marginLeft: 12 }}>
                  xG 客 <HighlightedValue value={monte_carlo.xg_away.toFixed(2)} />
                </span>
                <span style={{ marginLeft: 12 }}>
                  总 <HighlightedValue value={monte_carlo.xg_total.toFixed(2)} />
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6 }}>
                <span>主胜 <HighlightedValue value={`${(monte_carlo.probabilities_1x2.home * 100).toFixed(1)}%`} /></span>
                <span style={{ marginLeft: 12 }}>
                  平 <HighlightedValue value={`${(monte_carlo.probabilities_1x2.draw * 100).toFixed(1)}%`} />
                </span>
                <span style={{ marginLeft: 12 }}>
                  客胜 <HighlightedValue value={`${(monte_carlo.probabilities_1x2.away * 100).toFixed(1)}%`} />
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6 }}>
                <span>BTTS <HighlightedValue value={`${(monte_carlo.btts * 100).toFixed(1)}%`} /></span>
                <span style={{ marginLeft: 12 }}>
                  大2.5 <HighlightedValue value={`${(monte_carlo.over_2_5 * 100).toFixed(1)}%`} />
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", marginBottom: 6 }}>
                <span>半场 主 <HighlightedValue value={`${(monte_carlo.half_time_1x2.home * 100).toFixed(1)}%`} /></span>
                <span style={{ marginLeft: 12 }}>
                  平 <HighlightedValue value={`${(monte_carlo.half_time_1x2.draw * 100).toFixed(1)}%`} />
                </span>
                <span style={{ marginLeft: 12 }}>
                  客 <HighlightedValue value={`${(monte_carlo.half_time_1x2.away * 100).toFixed(1)}%`} />
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)", display: "flex", gap: 10 }}>
                {Object.entries(monte_carlo.correct_score)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([score, prob]) => (
                    <span key={score}>
                      {score} <HighlightedValue value={`${(prob * 100).toFixed(1)}%`} />
                    </span>
                  ))}
              </div>
            </Section>
          </>
        )}
      </div>
    </div>
  );
}
