import { type CSSProperties, type ReactNode, useState } from "react";
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

function numOrNull(v: unknown): number | null {
  const n = Number(v);
  return isNaN(n) || v == null ? null : n;
}

// ─── Shared types ─────────────────────────────────────────────────────────────

interface FtOdds {
  bookmaker: string;
  home?: { opening: number; closing: number };
  draw?: { opening: number; closing: number };
  away?: { opening: number; closing: number };
}

interface AHOdds {
  line: string;           // e.g. "+0.5", "-1", "0"
  homeOpen: number | null;
  homeNow: number | null;
  awayOpen: number | null;
  awayNow: number | null;
}

interface GLOdds {
  line: string;           // e.g. "2.5", "3"
  overOpen: number | null;
  overNow: number | null;
  underOpen: number | null;
  underNow: number | null;
}

interface TeamStatRow {
  teamId: unknown;
  name: string;
  xgFor: number | null;
  xgAgainst: number | null;
  goalsForAvg: number | null;
  goalsAgainstAvg: number | null;
  btts: number | null;       // percentage
  cleanSheet: number | null; // percentage
  failedToScore: number | null;
  over25: number | null;     // percentage
}

// ─── Data structures for each source ─────────────────────────────────────────

export interface SportmonksParsed {
  // 全场概率
  fulltime?: { home: number; draw: number; away: number };
  // 半场概率
  htFulltime?: { home: number; draw: number; away: number };
  // BTTS / 大小球
  btts_yes?: number;
  over15?: number;
  over25?: number;
  // 预测 xG（从 correct_score 分布推算）
  xgHome?: number | null;
  xgAway?: number | null;
  // 正确比分概率 top 6
  topScorelines: Array<{ score: string; pct: number }>;
  // H2H 历史
  h2h: H2HRecord[];
  // 历史 xG 对比
  historicalXg: {
    homeAvgXg: number | null;
    homeAvgXgAgainst: number | null;
    awayAvgXg: number | null;
    awayAvgXgAgainst: number | null;
  } | null;
  // 积分榜位置
  standings: {
    home?: { position: number; name: string; played: number; pts: number };
    away?: { position: number; name: string; played: number; pts: number };
  } | null;
  // 阵容
  lineupInfo?: string;
}

export interface MonteCarloParsed {
  homeWin: number | null;
  draw: number | null;
  awayWin: number | null;
  btts: number | null;
  o25: number | null;
  o15: number | null;
  o35: number | null;
  xgHome: number | null;
  xgAway: number | null;
  xgTotal: number | null;
  firstHalf?: { home: number | null; draw: number | null; away: number | null };
  topScorelines: Array<{ score: string; pct: number }>;
}

export interface H2HRecord {
  date: string;
  homeName: string;
  awayName: string;
  homeGoals: number;
  awayGoals: number;
  result: "home" | "draw" | "away";
  btts: boolean;
  over25: boolean;
}

export interface RecentFormStats {
  home5h: TeamStatRow | null;   // 主队近5场主场
  away5a: TeamStatRow | null;   // 客队近5场客场
  home10: TeamStatRow | null;   // 主队近10场总体
  away10: TeamStatRow | null;   // 客队近10场总体
}

export interface OddalertsParsed {
  ftOdds: FtOdds | null;
  ahOdds: AHOdds | null;
  glOdds: GLOdds | null;
  homeStats: TeamStatRow | null;
  awayStats: TeamStatRow | null;
  probability: {
    home_win?: number;
    draw?: number;
    away_win?: number;
    btts?: number;
    o25?: number;
  } | null;
  monteCarlo: MonteCarloParsed | null;
  h2h: H2HRecord[];
  recentForm: RecentFormStats | null;
  hasEmptyOdds: boolean;
}

// ─── OddAlerts line-value helpers (mirrors oa_main.py logic) ─────────────────

/** Convert OA outcome suffix like "05", "125", "m05", "p025", "1" → float */
function oaLineToFloat(raw: unknown): number {
  if (raw == null) return 0;
  let s = String(raw).trim();
  let neg = false;
  if (s.startsWith("m") || s.startsWith("-")) { neg = true; s = s.slice(1); }
  else if (s.startsWith("p")) { s = s.slice(1); }

  let val: number;
  if (s.length === 1) {
    val = parseInt(s, 10);
  } else if (s.length === 2) {
    val = s[1] === "0" ? parseInt(s[0], 10) : parseFloat(s[0] + "." + s[1]);
  } else if (s.length === 3) {
    val = s[2] === "0"
      ? parseFloat(s[0] + "." + s[1])
      : parseFloat(s[0] + "." + s[1] + s[2]);
  } else {
    val = parseFloat(s) || 0;
  }
  return neg ? -val : val;
}

/** Format AH line float → display string: "+0.5", "-1", "0" */
function fmtLine(v: number): string {
  if (v === 0) return "0";
  const s = Math.abs(v) % 1 === 0 ? Math.abs(v).toFixed(0) : Math.abs(v).toFixed(2).replace(/0+$/, "");
  return (v > 0 ? "+" : "-") + s;
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
      const opening = numOrNull(o.opening);
      const closing = numOrNull(o.closing);
      const pair = { opening: opening ?? closing ?? 0, closing: closing ?? opening ?? 0 };
      if (outcome === "home") r.home = pair;
      else if (outcome === "draw") r.draw = pair;
      else if (outcome === "away") r.away = pair;
    }
    if (r.home || r.draw || r.away) return r;
  }
  return null;
}

/**
 * Extract Pinnacle Asian Handicap: find the most balanced line (home ≈ away odds).
 * Returns HK-odds (euro - 1). Mirrors oa_main.py fetch_pinnacle_odds logic.
 */
export function extractPinnacleAH(rows: Array<Record<string, unknown>>): AHOdds | null {
  const ahRows = rows.filter(
    (o) => o.bookmaker_name === "Pinnacle" && o.market_key === "asian_handicap"
  );
  if (!ahRows.length) return null;

  // Group by outcome line suffix: "home_05" → side="home", line="05"
  const byLine: Record<string, { home?: { open: number; now: number }; away?: { open: number; now: number } }> = {};
  for (const o of ahRows) {
    const outcome = String(o.outcome || "");
    const under = outcome.indexOf("_");
    if (under < 0) continue;
    const side = outcome.slice(0, under);   // "home" | "away"
    const lineSuffix = outcome.slice(under + 1); // "05", "m125", etc.
    if (!byLine[lineSuffix]) byLine[lineSuffix] = {};
    const opening = numOrNull(o.opening);
    const closing = numOrNull(o.closing);
    if (opening != null || closing != null) {
      byLine[lineSuffix][side as "home" | "away"] = {
        open: (opening ?? closing ?? 0) - 1,
        now: (closing ?? opening ?? 0) - 1,
      };
    }
  }

  if (!Object.keys(byLine).length) return null;

  // Pick the line where |home_open - away_open| is smallest and both ~0.7-1.3 HK
  const VALID = (v: number) => v >= 0.6 && v <= 1.3;
  let bestLine = "";
  let bestScore = Infinity;
  for (const [lineSuffix, sides] of Object.entries(byLine)) {
    const h = sides.home?.open;
    const a = sides.away?.open;
    if (h == null || a == null) continue;
    const score = VALID(h) && VALID(a) ? Math.abs(h - a) : 999;
    if (score < bestScore) { bestScore = score; bestLine = lineSuffix; }
  }
  if (!bestLine && Object.keys(byLine).length) bestLine = Object.keys(byLine)[0];

  const sides = byLine[bestLine];
  const lineFloat = oaLineToFloat(bestLine);
  return {
    line: fmtLine(lineFloat),
    homeOpen: sides?.home?.open ?? null,
    homeNow: sides?.home?.now ?? null,
    awayOpen: sides?.away?.open ?? null,
    awayNow: sides?.away?.now ?? null,
  };
}

/**
 * Extract Pinnacle Goal Line (asian over/under). Picks most balanced line.
 * Returns HK-odds (euro - 1).
 */
export function extractPinnacleGL(rows: Array<Record<string, unknown>>): GLOdds | null {
  let glRows = rows.filter(
    (o) => o.bookmaker_name === "Pinnacle" && o.market_key === "goal_line"
  );
  if (!glRows.length) {
    glRows = rows.filter(
      (o) => o.bookmaker_name === "Pinnacle" && o.market_key === "total_goals"
    );
  }
  if (!glRows.length) return null;

  const byLine: Record<string, { over?: { open: number; now: number }; under?: { open: number; now: number } }> = {};
  for (const o of glRows) {
    const outcome = String(o.outcome || ""); // "over_3", "under_35"
    const under = outcome.indexOf("_");
    if (under < 0) continue;
    const side = outcome.slice(0, under);
    const lineSuffix = outcome.slice(under + 1);
    const lineFmt = lineSuffix.length === 2 && lineSuffix[1] !== "0"
      ? lineSuffix[0] + "." + lineSuffix[1]
      : lineSuffix.replace(/0+$/, "") || lineSuffix;
    if (!byLine[lineFmt]) byLine[lineFmt] = {};
    const opening = numOrNull(o.opening);
    const closing = numOrNull(o.closing);
    if (opening != null || closing != null) {
      byLine[lineFmt][side as "over" | "under"] = {
        open: (opening ?? closing ?? 0) - 1,
        now: (closing ?? opening ?? 0) - 1,
      };
    }
  }

  if (!Object.keys(byLine).length) return null;

  const VALID = (v: number) => v >= 0.6 && v <= 1.3;
  let bestLine = "";
  let bestScore = Infinity;
  for (const [lineFmt, sides] of Object.entries(byLine)) {
    const ov = sides.over?.open;
    const un = sides.under?.open;
    if (ov == null || un == null) continue;
    const score = VALID(ov) && VALID(un) ? Math.abs(ov - un) : 999;
    if (score < bestScore) { bestScore = score; bestLine = lineFmt; }
  }
  if (!bestLine && Object.keys(byLine).length) bestLine = Object.keys(byLine)[0];

  const sides = byLine[bestLine];
  return {
    line: bestLine,
    overOpen: sides?.over?.open ?? null,
    overNow: sides?.over?.now ?? null,
    underOpen: sides?.under?.open ?? null,
    underNow: sides?.under?.now ?? null,
  };
}

/** Extract team stat row from OA stats.data[] */
function extractTeamStatRow(teamData: Record<string, unknown>): TeamStatRow {
  const gf = teamData.goals_for as Record<string, unknown> | undefined;
  const ga = teamData.goals_against as Record<string, unknown> | undefined;
  const bttsField = teamData.btts as Record<string, unknown> | undefined;
  const cs = teamData.clean_sheet as Record<string, unknown> | undefined;
  const fts = teamData.failed_to_score as Record<string, unknown> | undefined;
  const goalsOver = teamData.goals_over as Record<string, unknown> | undefined;
  const o2 = goalsOver?.o2 as Record<string, unknown> | undefined;

  return {
    teamId: teamData.team_id,
    name: String(teamData.name || ""),
    xgFor: numOrNull((teamData.xg_for as Record<string, unknown> | undefined)?.total_avg ?? teamData.xg_for),
    xgAgainst: numOrNull((teamData.xg_against as Record<string, unknown> | undefined)?.total_avg ?? teamData.xg_against),
    goalsForAvg: numOrNull(gf?.total_avg),
    goalsAgainstAvg: numOrNull(ga?.total_avg),
    btts: numOrNull(bttsField?.total_percentage),
    cleanSheet: numOrNull(cs?.total_percentage),
    failedToScore: numOrNull(fts?.total_percentage),
    over25: numOrNull(o2?.total_percentage),
  };
}

/** Extract H2H records from SportMonks raw fixture list (different schema than OddAlerts) */
function extractSmH2H(raw: unknown): H2HRecord[] {
  if (!Array.isArray(raw)) return [];
  return (raw as Array<Record<string, unknown>>)
    .filter((r): r is Record<string, unknown> => r != null && typeof r === "object")
    .map((r): H2HRecord | null => {
      // team names from participants array
      const parts = r.participants as Array<Record<string, unknown>> | undefined;
      let homeName = "", awayName = "";
      if (Array.isArray(parts)) {
        for (const p of parts) {
          const loc = (p.meta as Record<string, unknown> | undefined)?.location;
          if (loc === "home") homeName = String(p.name || "");
          else if (loc === "away") awayName = String(p.name || "");
        }
      }
      // score from scores array — look for 2ND_HALF or CURRENT (final)
      let homeGoals = 0, awayGoals = 0, foundScore = false;
      const scores = r.scores as Array<Record<string, unknown>> | undefined;
      if (Array.isArray(scores)) {
        // Prefer "2ND_HALF" (cumulative FT) > "CURRENT"
        const priority = ["2ND_HALF", "CURRENT", "FT", "FULLTIME"];
        for (const desc of priority) {
          const matching = scores.filter(
            (s) => String(s.description ?? "").toUpperCase() === desc
          );
          if (matching.length >= 2) {
            for (const s of matching) {
              const loc = String(s.participant ?? s.location ?? "");
              const g = Number(s.score ?? s.goals ?? 0);
              if (loc === "home") homeGoals = g;
              else if (loc === "away") awayGoals = g;
            }
            foundScore = true;
            break;
          }
        }
      }
      if (!foundScore && !homeName && !awayName) return null;
      const date = String(r.starting_at ?? r.date ?? "").slice(0, 10);
      return {
        date,
        homeName,
        awayName,
        homeGoals,
        awayGoals,
        result: homeGoals > awayGoals ? "home" : homeGoals < awayGoals ? "away" : "draw",
        btts: homeGoals > 0 && awayGoals > 0,
        over25: homeGoals + awayGoals > 2,
      };
    })
    .filter((r): r is H2HRecord => r !== null)
    .slice(0, 6);
}

/** Extract standings row for a given participant_id */
function extractSmStandingRow(
  rows: Array<Record<string, unknown>>,
  participantId: unknown,
): { position: number; name: string; played: number; pts: number } | undefined {
  if (participantId == null) return undefined;
  const row = rows.find((r) => {
    const pid = r.participant_id ?? (r.participant as Record<string, unknown> | undefined)?.id;
    return pid === participantId;
  });
  if (!row) return undefined;
  const part = row.participant as Record<string, unknown> | undefined;
  const name = String(part?.name ?? row.team_name ?? "");
  const position = Number(row.position ?? 0);
  const pts = Number(row.points ?? 0);
  // details is a list of {type_id, value} where type_id varies by provider version
  const details = row.details as Array<Record<string, unknown>> | undefined;
  let played = 0;
  if (Array.isArray(details)) {
    // SportMonks type_id 130 = games played, fallback: find item with key "played"
    const match =
      details.find((d) => d.type_id === 130 || String(d.type_id) === "130") ??
      details.find((d) => String(d.type ?? d.name ?? "").toLowerCase().includes("play"));
    played = Number(match?.value ?? match?.total ?? 0);
  }
  return { position, name, played, pts };
}

export function extractSportmonksPreds(data: Record<string, unknown>): SportmonksParsed {
  const fixture = data.fixture as Record<string, unknown> | undefined;
  const summary = data.predictions_summary as Record<string, Record<string, number>> | undefined;
  const predXg = data.predictive_xg as Record<string, number> | undefined;
  const histXg = data.historical_xg_comparison as Record<string, Record<string, unknown>> | undefined;

  const result: SportmonksParsed = { topScorelines: [], h2h: [], historicalXg: null, standings: null };

  // ── 1X2 ──────────────────────────────────────────────────────────────
  const s1x2 = summary?.["1x2"] ?? summary?.["fulltime_result"];
  if (s1x2) {
    const h = numOrNull(s1x2.home), d = numOrNull(s1x2.draw), a = numOrNull(s1x2.away);
    if (h != null && d != null && a != null) result.fulltime = { home: h, draw: d, away: a };
  }

  // ── 半场 1X2 ─────────────────────────────────────────────────────────
  const sHt = summary?.["ht_1x2"];
  if (sHt) {
    const h = numOrNull(sHt.home), d = numOrNull(sHt.draw), a = numOrNull(sHt.away);
    if (h != null && d != null && a != null) result.htFulltime = { home: h, draw: d, away: a };
  }

  // ── BTTS / 大小球 ────────────────────────────────────────────────────
  const sBtts = summary?.["btts"];
  if (sBtts) result.btts_yes = numOrNull(sBtts.yes) ?? undefined;

  const sOu25 = summary?.["over_under_2_5"];
  if (sOu25) result.over25 = numOrNull(sOu25.yes) ?? undefined;

  const sOu15 = summary?.["over_under_1_5"];
  if (sOu15) result.over15 = numOrNull(sOu15.yes) ?? undefined;

  // ── 预测 xG ─────────────────────────────────────────────────────────
  if (predXg) {
    result.xgHome = numOrNull(predXg.home);
    result.xgAway = numOrNull(predXg.away);
  }

  // ── 正确比分 top 6 ──────────────────────────────────────────────────
  const sCs = summary?.["correct_score"] as unknown;
  const scoresObj =
    (sCs as Record<string, unknown> | undefined)?.scores ??
    (typeof sCs === "object" && sCs !== null && !Array.isArray(sCs) ? sCs : undefined);
  if (scoresObj && typeof scoresObj === "object") {
    result.topScorelines = Object.entries(scoresObj as Record<string, unknown>)
      .filter(([k, v]) => !k.startsWith("Other") && typeof v === "number")
      .sort(([, a], [, b]) => (b as number) - (a as number))
      .slice(0, 6)
      .map(([score, pct]) => ({ score, pct: pct as number }));
  }

  // ── H2H ────────────────────────────────────────────────────────────
  result.h2h = extractSmH2H(data.h2h);

  // ── 历史 xG ────────────────────────────────────────────────────────
  if (histXg) {
    result.historicalXg = {
      homeAvgXg: numOrNull(histXg.home_team?.avg_xg),
      homeAvgXgAgainst: numOrNull(histXg.home_team?.avg_xg_against),
      awayAvgXg: numOrNull(histXg.away_team?.avg_xg),
      awayAvgXgAgainst: numOrNull(histXg.away_team?.avg_xg_against),
    };
  }

  // ── 积分榜 ──────────────────────────────────────────────────────────
  const standingsRaw = data.standings as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(standingsRaw) && standingsRaw.length) {
    const parts = fixture?.participants as Array<Record<string, unknown>> | undefined;
    let homeId: unknown, awayId: unknown;
    if (Array.isArray(parts)) {
      for (const p of parts) {
        const loc = (p.meta as Record<string, unknown> | undefined)?.location;
        if (loc === "home") homeId = p.id;
        else if (loc === "away") awayId = p.id;
      }
    }
    const home = extractSmStandingRow(standingsRaw, homeId);
    const away = extractSmStandingRow(standingsRaw, awayId);
    if (home || away) result.standings = { home, away };
  }

  // ── 阵容 ────────────────────────────────────────────────────────────
  const lineups = (fixture?.lineups ?? data.lineups) as Array<Record<string, unknown>> | undefined;
  if (Array.isArray(lineups) && lineups.length) {
    const parts = fixture?.participants as Array<Record<string, unknown>> | undefined;
    let homeId: unknown, awayId: unknown;
    if (Array.isArray(parts)) {
      for (const p of parts) {
        const loc = (p.meta as Record<string, unknown> | undefined)?.location;
        if (loc === "home") homeId = p.id;
        else if (loc === "away") awayId = p.id;
      }
    }
    const homeCount = homeId ? lineups.filter((l) => l.participant_id === homeId || l.team_id === homeId).length : Math.floor(lineups.length / 2);
    const awayCount = awayId ? lineups.filter((l) => l.participant_id === awayId || l.team_id === awayId).length : lineups.length - homeCount;
    if (homeCount + awayCount > 0) result.lineupInfo = `主 ${homeCount}人 | 客 ${awayCount}人`;
  }

  return result;
}

/** 从 data.predictions（蒙特卡洛结果）提取关键指标 */
export function extractMonteCarlo(raw: unknown): MonteCarloParsed | null {
  if (!raw || typeof raw !== "object") return null;
  const d = raw as Record<string, unknown>;

  const xgField = d.expected_goals as Record<string, unknown> | undefined;
  const firstHalfField = d.first_half as Record<string, unknown> | undefined;

  // Top scorelines（只取概率≥5%的，按概率降序）
  const slRaw = d.scorelines as Record<string, number> | undefined;
  const topScorelines = slRaw
    ? Object.entries(slRaw)
        .filter(([k, v]) => !k.startsWith("other") && typeof v === "number" && v >= 5)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 6)
        .map(([score, pct]) => ({ score: score.replace("_", "-"), pct }))
    : [];

  const result: MonteCarloParsed = {
    homeWin: numOrNull(d.home_win_percentage),
    draw:    numOrNull(d.draw_percentage),
    awayWin: numOrNull(d.away_win_percentage),
    btts:    numOrNull(d.btts_percentage),
    o25:     numOrNull(d.o25_goals_percentage),
    o15:     numOrNull(d.o15_goals_percentage),
    o35:     numOrNull(d.o35_goals_percentage),
    xgHome:  numOrNull(xgField?.home),
    xgAway:  numOrNull(xgField?.away),
    xgTotal: numOrNull(xgField?.total),
    firstHalf: firstHalfField
      ? {
          home: numOrNull(firstHalfField.home_win_percentage),
          draw: numOrNull(firstHalfField.draw_percentage),
          away: numOrNull(firstHalfField.away_win_percentage),
        }
      : undefined,
    topScorelines,
  };

  const hasAny = result.homeWin != null || result.xgHome != null || topScorelines.length > 0;
  return hasAny ? result : null;
}

/** 从 data.h2h[]（对阵历史）提取结构化记录 */
export function extractH2H(raw: unknown): H2HRecord[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .filter((r): r is Record<string, unknown> => r != null && typeof r === "object")
    .map((r) => ({
      date:       String(r.date || r.unix || ""),
      homeName:   String(r.home_name || ""),
      awayName:   String(r.away_name || ""),
      homeGoals:  Number(r.home_goals ?? 0),
      awayGoals:  Number(r.away_goals ?? 0),
      result:     r.home_win ? "home" : r.away_win ? "away" : "draw",
      btts:       Boolean(r.btts),
      over25:     Boolean(r.over_25),
    } as H2HRecord));
}

/** 从 data.recent_stats 提取近期状态 */
export function extractRecentForm(raw: unknown): RecentFormStats | null {
  if (!raw || typeof raw !== "object") return null;
  const d = raw as Record<string, unknown>;
  const parse = (v: unknown) =>
    v && typeof v === "object" ? extractTeamStatRow(v as Record<string, unknown>) : null;
  return {
    home5h: parse(d.home_5h),
    away5a: parse(d.away_5a),
    home10: parse(d.home_10),
    away10: parse(d.away_10),
  };
}

export function extractOddalertsData(data: Record<string, unknown>): OddalertsParsed {
  const fixtureData = data.fixture as Record<string, unknown> | undefined;
  const homeId = fixtureData?.home_id;
  const awayId = fixtureData?.away_id;

  const oddsRows = (data.odds_history as { data?: unknown[] } | undefined)?.data as
    | Array<Record<string, unknown>>
    | undefined;

  const ftOdds = oddsRows?.length ? extractFtOdds(oddsRows) : null;
  const ahOdds = oddsRows?.length ? extractPinnacleAH(oddsRows) : null;
  const glOdds = oddsRows?.length ? extractPinnacleGL(oddsRows) : null;

  // Fixture-type overall stats
  let homeStats: TeamStatRow | null = null;
  let awayStats: TeamStatRow | null = null;
  const statsRows = (data.stats as { data?: unknown[] } | undefined)?.data as
    | Array<Record<string, unknown>>
    | undefined;
  if (statsRows?.length) {
    const hRow = homeId ? statsRows.find((t) => t.team_id === homeId) : statsRows[0];
    const aRow = awayId ? statsRows.find((t) => t.team_id === awayId) : statsRows[1];
    if (hRow) homeStats = extractTeamStatRow(hRow);
    if (aRow) awayStats = extractTeamStatRow(aRow);
  }

  // Probability model
  const rawProb = (fixtureData?.probability ?? data.probability) as Record<string, number> | undefined;
  const probability = rawProb
    ? { home_win: rawProb.home_win, draw: rawProb.draw, away_win: rawProb.away_win, btts: rawProb.btts, o25: rawProb.o25 }
    : null;

  // Monte Carlo simulation
  const monteCarlo = extractMonteCarlo(data.predictions);

  // H2H
  const h2h = extractH2H(data.h2h);

  // Recent form
  const recentForm = extractRecentForm(data.recent_stats);

  return {
    ftOdds, ahOdds, glOdds,
    homeStats, awayStats,
    probability,
    monteCarlo,
    h2h,
    recentForm,
    hasEmptyOdds: oddsRows != null && oddsRows.length === 0,
  };
}

// ─── MetricItem ───────────────────────────────────────────────────────────────

export function MetricItem({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "baseline" }}>
      <span style={{ fontSize: 12, color: "var(--text-muted)", flexShrink: 0 }}>{label}</span>
      <span style={{
        fontSize: 13, fontFamily: "var(--font-mono)",
        color: highlight ? "var(--accent)" : "var(--text-secondary)",
        fontWeight: highlight ? 600 : 400,
      }}>{value}</span>
    </div>
  );
}

// ─── Section header ───────────────────────────────────────────────────────────

function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 700,
      color: "var(--text-secondary)",
      borderLeft: "2px solid var(--accent)",
      paddingLeft: 6,
      marginBottom: 6, marginTop: 8,
      lineHeight: 1.2,
    }}>
      {children}
    </div>
  );
}

// ─── Collapsible section ──────────────────────────────────────────────────────

function CollapsibleSection({ title, children, defaultOpen = true }: {
  title: ReactNode; children: ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          width: "100%", background: "rgba(255,255,255,0.04)",
          border: "none", borderLeft: "2px solid var(--accent)",
          borderRadius: "2px 4px 4px 2px",
          padding: "5px 8px 5px 6px",
          cursor: "pointer",
          color: "var(--text-secondary)", fontSize: 12, fontWeight: 700,
          marginBottom: open ? 8 : 0, marginTop: 8,
          textAlign: "left",
        }}
      >
        <span>{title}</span>
        <span style={{ fontSize: 10, color: "var(--text-muted)", marginLeft: 8 }}>
          {open ? "▴" : "▾"}
        </span>
      </button>
      {open && children}
    </div>
  );
}

// ─── Odds move arrow ──────────────────────────────────────────────────────────

function MoveArrow({ open: openVal, now }: { open: number | null; now: number | null }) {
  if (openVal == null || now == null) return null;
  const diff = now - openVal;
  if (Math.abs(diff) < 0.005) return null;
  // For HK odds: lower odds = more favoured. Odds decrease = team strengthened.
  const color = diff < 0 ? "#22c55e" : "#ef4444";
  const arrow = diff < 0 ? "↓" : "↑";
  return (
    <span style={{ fontSize: 10, color, marginLeft: 2, fontFamily: "var(--font-mono)" }}>
      {arrow}{Math.abs(diff).toFixed(2)}
    </span>
  );
}

// ─── Odds mini-table: Opening | Now | Move ───────────────────────────────────

interface OddsRowProps {
  label: string;
  homeOpen: number | null;
  homeNow: number | null;
  awayOpen: number | null;
  awayNow: number | null;
  midLabel?: string;
  sideLabel?: string; // "大" | "小" etc
}

function OddsCompactRow({
  label, homeOpen, homeNow, awayOpen, awayNow, midLabel, sideLabel,
}: OddsRowProps) {
  const cellStyle: CSSProperties = {
    fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--text-secondary)",
    whiteSpace: "nowrap",
  };
  const nowStyle: CSSProperties = { ...cellStyle, color: "var(--text)", fontWeight: 600 };

  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
      <span style={{ fontSize: 11, color: "var(--text-muted)", minWidth: 30, flexShrink: 0 }}>{label}</span>
      {/* Home / Over */}
      <span style={{ ...nowStyle }}>
        {sideLabel ? sideLabel + " " : "主 "}
        {homeNow != null ? homeNow.toFixed(2) : "—"}
        <MoveArrow open={homeOpen} now={homeNow} />
      </span>
      {midLabel && (
        <span style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 4px" }}>{midLabel}</span>
      )}
      {/* Away / Under */}
      <span style={{ ...cellStyle }}>
        {sideLabel ? "小 " : "客 "}
        {awayNow != null ? awayNow.toFixed(2) : "—"}
        <MoveArrow open={awayOpen} now={awayNow} />
      </span>
      {/* Opening reference */}
      {(homeOpen != null || awayOpen != null) && (
        <span style={{ fontSize: 11, color: "var(--text-muted)", marginLeft: 6 }}>
          (开 {homeOpen != null ? homeOpen.toFixed(2) : "—"} / {awayOpen != null ? awayOpen.toFixed(2) : "—"})
        </span>
      )}
    </div>
  );
}

// ─── FT result odds (with draw) ───────────────────────────────────────────────

function FtOddsRow({ odds }: { odds: FtOdds }) {
  const homeMove = odds.home && odds.home.opening !== odds.home.closing
    ? odds.home.closing - odds.home.opening : null;
  const drawMove = odds.draw && odds.draw.opening !== odds.draw.closing
    ? odds.draw.closing - odds.draw.opening : null;
  const awayMove = odds.away && odds.away.opening !== odds.away.closing
    ? odds.away.closing - odds.away.opening : null;

  const cellStyle: CSSProperties = {
    fontFamily: "var(--font-mono)", fontSize: 13, whiteSpace: "nowrap",
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      <SectionLabel>1X2 · {odds.bookmaker}</SectionLabel>
      <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
        {[
          { label: "主胜", val: odds.home?.closing, move: homeMove, open: odds.home?.opening },
          { label: "平局", val: odds.draw?.closing, move: drawMove, open: odds.draw?.opening },
          { label: "客胜", val: odds.away?.closing, move: awayMove, open: odds.away?.opening },
        ].map(({ label, val, move, open }) => (
          <div key={label} style={{ display: "flex", alignItems: "baseline", gap: 3 }}>
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{label}</span>
            <span style={{ ...cellStyle, color: "var(--text)", fontWeight: 600 }}>
              {val != null ? val.toFixed(2) : "—"}
            </span>
            {move != null && Math.abs(move) >= 0.005 && (
              <span style={{ fontSize: 11, color: move < 0 ? "#22c55e" : "#ef4444", fontFamily: "var(--font-mono)" }}>
                {move < 0 ? "↓" : "↑"}{Math.abs(move).toFixed(2)}
              </span>
            )}
            {open != null && open !== val && (
              <span style={{ fontSize: 11, color: "var(--text-muted)" }}>({open.toFixed(2)})</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Team stats table ─────────────────────────────────────────────────────────

function TeamStatsTable({ home, away, homeTeam, awayTeam }: {
  home: TeamStatRow | null;
  away: TeamStatRow | null;
  homeTeam: string;
  awayTeam: string;
}) {
  const rows: Array<{
    label: string;
    hVal: number | null;
    aVal: number | null;
    pct?: boolean;
    d?: number;
  }> = [
    { label: "xG 进攻", hVal: home?.xgFor ?? null, aVal: away?.xgFor ?? null },
    { label: "xG 防守", hVal: home?.xgAgainst ?? null, aVal: away?.xgAgainst ?? null },
    { label: "场均进球", hVal: home?.goalsForAvg ?? null, aVal: away?.goalsForAvg ?? null },
    { label: "场均失球", hVal: home?.goalsAgainstAvg ?? null, aVal: away?.goalsAgainstAvg ?? null },
    { label: "BTTS", hVal: home?.btts ?? null, aVal: away?.btts ?? null, pct: true, d: 0 },
    { label: "大2.5", hVal: home?.over25 ?? null, aVal: away?.over25 ?? null, pct: true, d: 0 },
    { label: "零封率", hVal: home?.cleanSheet ?? null, aVal: away?.cleanSheet ?? null, pct: true, d: 0 },
    { label: "未进球", hVal: home?.failedToScore ?? null, aVal: away?.failedToScore ?? null, pct: true, d: 0 },
  ];

  const hasAny = rows.some((r) => r.hVal != null || r.aVal != null);
  if (!hasAny) return null;

  const homeLabel = home?.name || homeTeam || "主队";
  const awayLabel = away?.name || awayTeam || "客队";

  const valStyle: CSSProperties = {
    fontFamily: "var(--font-mono)", fontSize: 12, textAlign: "right",
  };

  return (
    <CollapsibleSection title="球队统计（赛季快照）" defaultOpen={false}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", fontSize: 11, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4, width: 76 }} />
            <th style={{ ...valStyle, fontWeight: 600, color: "var(--text)", paddingBottom: 4, paddingLeft: 12 }}>
              {homeLabel}
            </th>
            <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-secondary)", paddingBottom: 4, paddingLeft: 12 }}>
              {awayLabel}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label, hVal, aVal, pct, d = 2 }) => {
            if (hVal == null && aVal == null) return null;
            const fmtVal = (v: number | null) => v == null ? "—" : pct ? v.toFixed(d) + "%" : v.toFixed(d);
            const higherIsBetter = !label.includes("防守") && !label.includes("失球") && !label.includes("未进球");
            const hHighlight = hVal != null && aVal != null && (higherIsBetter ? hVal > aVal : hVal < aVal);
            const aHighlight = hVal != null && aVal != null && (higherIsBetter ? aVal > hVal : aVal < hVal);
            return (
              <tr key={label}>
                <td style={{ fontSize: 11, color: "var(--text-muted)", paddingBottom: 2 }}>{label}</td>
                <td style={{
                  ...valStyle, paddingLeft: 12,
                  color: hHighlight ? "var(--accent)" : "var(--text-secondary)",
                  fontWeight: hHighlight ? 600 : 400,
                }}>
                  {fmtVal(hVal)}
                </td>
                <td style={{
                  ...valStyle, paddingLeft: 12,
                  color: aHighlight ? "var(--accent)" : "var(--text-muted)",
                  fontWeight: aHighlight ? 600 : 400,
                }}>
                  {fmtVal(aVal)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </CollapsibleSection>
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
  const hasBody = !noData && children;
  return (
    <div style={{
      background: "var(--card-bg)", border: "1px solid var(--border)",
      borderRadius: "var(--radius-md)", overflow: "hidden",
      boxShadow: "0 1px 4px rgba(0,0,0,0.35)",
    }}>
      {/* Header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 12px",
        background: "rgba(255,255,255,0.03)",
        borderBottom: hasBody ? "1px solid var(--border)" : "none",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{icon} {title}</span>
          {collectedAt && (
            <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
              {dayjs(collectedAt).format("MM-DD HH:mm")}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
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

      {/* Body */}
      {noData ? (
        <div style={{ padding: "8px 12px" }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无数据</span>
        </div>
      ) : (
        <div style={{ padding: "10px 12px" }}>
          {children}
        </div>
      )}
    </div>
  );
}

// ─── Per-source metrics ───────────────────────────────────────────────────────

export function SportmonksMetrics({ data, homeTeam, awayTeam }: {
  data: Record<string, unknown>; homeTeam: string; awayTeam: string;
}) {
  const parsed = extractSportmonksPreds(data);

  const hasContent = parsed.fulltime || parsed.xgHome != null || parsed.btts_yes != null
    || parsed.topScorelines.length > 0 || parsed.h2h.length > 0 || parsed.historicalXg || parsed.standings;

  if (!hasContent) {
    return <span style={{ fontSize: 12, color: "var(--text-muted)" }}>暂无数据</span>;
  }

  const valStyle: CSSProperties = { fontFamily: "var(--font-mono)", fontSize: 12, textAlign: "right", paddingLeft: 12 };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>

      {/* 全场概率 1X2 */}
      {parsed.fulltime && (
        <div>
          <SectionLabel>全场胜平负概率</SectionLabel>
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <MetricItem label={`${homeTeam || "主"} 胜`} value={`${parsed.fulltime.home.toFixed(1)}%`} highlight={parsed.fulltime.home > parsed.fulltime.away} />
            <MetricItem label="平" value={`${parsed.fulltime.draw.toFixed(1)}%`} />
            <MetricItem label={`${awayTeam || "客"} 胜`} value={`${parsed.fulltime.away.toFixed(1)}%`} highlight={parsed.fulltime.away > parsed.fulltime.home} />
          </div>
        </div>
      )}

      {/* 预测 xG + BTTS/大小球 */}
      {(parsed.xgHome != null || parsed.xgAway != null || parsed.btts_yes != null || parsed.over25 != null) && (
        <div style={{ display: "flex", gap: 20, flexWrap: "wrap", marginTop: 4 }}>
          {parsed.xgHome != null && <MetricItem label="xG 主" value={fmt(parsed.xgHome)} highlight />}
          {parsed.xgAway != null && <MetricItem label="xG 客" value={fmt(parsed.xgAway)} highlight />}
          {parsed.btts_yes != null && <MetricItem label="BTTS" value={`${parsed.btts_yes.toFixed(1)}%`} />}
          {parsed.over25 != null && <MetricItem label="大2.5" value={`${parsed.over25.toFixed(1)}%`} />}
          {parsed.over15 != null && <MetricItem label="大1.5" value={`${parsed.over15.toFixed(1)}%`} />}
        </div>
      )}

      {/* 半场 1X2 */}
      {parsed.htFulltime && (
        <div>
          <SectionLabel>半场胜平负</SectionLabel>
          <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
            <MetricItem label={`${homeTeam || "主"} 胜`} value={`${parsed.htFulltime.home.toFixed(1)}%`} highlight={parsed.htFulltime.home > parsed.htFulltime.away} />
            <MetricItem label="平" value={`${parsed.htFulltime.draw.toFixed(1)}%`} />
            <MetricItem label={`${awayTeam || "客"} 胜`} value={`${parsed.htFulltime.away.toFixed(1)}%`} highlight={parsed.htFulltime.away > parsed.htFulltime.home} />
          </div>
        </div>
      )}

      {/* 阵容 */}
      {parsed.lineupInfo && (
        <div style={{ marginTop: 2 }}>
          <MetricItem label="阵容" value={parsed.lineupInfo} />
        </div>
      )}

      {/* 正确比分 top 6 */}
      {parsed.topScorelines.length > 0 && (
        <CollapsibleSection title="正确比分概率">
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
            {parsed.topScorelines.map(({ score, pct }) => (
              <span key={score} style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--text)" }}>{score}</span>
                <span style={{ color: "var(--text-muted)", marginLeft: 3 }}>{pct.toFixed(1)}%</span>
              </span>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* H2H */}
      {parsed.h2h.length > 0 && (
        <H2HSection records={parsed.h2h} homeTeam={homeTeam} awayTeam={awayTeam} />
      )}

      {/* 历史 xG 对比 */}
      {parsed.historicalXg && (
        <CollapsibleSection title="历史 xG（近10场）" defaultOpen={false}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", fontSize: 11, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4, width: 76 }} />
                <th style={{ ...valStyle, fontWeight: 600, color: "var(--text)", paddingBottom: 4 }}>{homeTeam || "主队"}</th>
                <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-secondary)", paddingBottom: 4 }}>{awayTeam || "客队"}</th>
              </tr>
            </thead>
            <tbody>
              {([
                { label: "场均进攻 xG", h: parsed.historicalXg.homeAvgXg, a: parsed.historicalXg.awayAvgXg, higherBetter: true },
                { label: "场均防守 xGA", h: parsed.historicalXg.homeAvgXgAgainst, a: parsed.historicalXg.awayAvgXgAgainst, higherBetter: false },
              ] as Array<{ label: string; h: number | null; a: number | null; higherBetter: boolean }>).map(({ label, h, a, higherBetter }) => {
                if (h == null && a == null) return null;
                const hWin = h != null && a != null && (higherBetter ? h > a : h < a);
                const aWin = h != null && a != null && (higherBetter ? a > h : a < h);
                return (
                  <tr key={label}>
                    <td style={{ fontSize: 11, color: "var(--text-muted)", paddingBottom: 2 }}>{label}</td>
                    <td style={{ ...valStyle, color: hWin ? "var(--accent)" : "var(--text-secondary)", fontWeight: hWin ? 600 : 400 }}>
                      {h != null ? h.toFixed(2) : "—"}
                    </td>
                    <td style={{ ...valStyle, color: aWin ? "var(--accent)" : "var(--text-muted)", fontWeight: aWin ? 600 : 400 }}>
                      {a != null ? a.toFixed(2) : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </CollapsibleSection>
      )}

      {/* 积分榜 */}
      {parsed.standings && (parsed.standings.home || parsed.standings.away) && (
        <CollapsibleSection title="联赛积分榜" defaultOpen={false}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", fontSize: 11, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4 }}>球队</th>
                <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4 }}>名次</th>
                <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4 }}>场次</th>
                <th style={{ ...valStyle, fontWeight: 600, color: "var(--text)", paddingBottom: 4 }}>积分</th>
              </tr>
            </thead>
            <tbody>
              {[parsed.standings.home, parsed.standings.away].filter(Boolean).map((row) => (
                <tr key={row!.name}>
                  <td style={{ fontSize: 11, color: "var(--text-secondary)", paddingBottom: 2 }}>{row!.name}</td>
                  <td style={{ ...valStyle, color: "var(--text-muted)" }}>{row!.position}</td>
                  <td style={{ ...valStyle, color: "var(--text-muted)" }}>{row!.played || "—"}</td>
                  <td style={{ ...valStyle, color: "var(--accent)", fontWeight: 600 }}>{row!.pts}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CollapsibleSection>
      )}

    </div>
  );
}

// ─── Monte Carlo display ──────────────────────────────────────────────────────

const DIVERGE_THRESHOLD = 7;


function MonteCarloSection({ mc, prob }: {
  mc: MonteCarloParsed;
  prob: OddalertsParsed["probability"];
}) {
  const pRows: Array<{ label: string; sim: number | null; model?: number }> = [
    { label: "主胜", sim: mc.homeWin, model: prob?.home_win },
    { label: "平局", sim: mc.draw,    model: prob?.draw },
    { label: "客胜", sim: mc.awayWin, model: prob?.away_win },
    { label: "BTTS", sim: mc.btts,    model: prob?.btts },
    { label: "大2.5", sim: mc.o25,   model: prob?.o25 },
  ];

  const valStyle: CSSProperties = {
    fontFamily: "var(--font-mono)", fontSize: 12, textAlign: "right", paddingLeft: 12,
  };

  return (
    <CollapsibleSection title="蒙特卡洛模拟（50k 次）">

      {/* xG */}
      {(mc.xgHome != null || mc.xgAway != null) && (
        <div style={{ display: "flex", gap: 20, marginBottom: 8 }}>
          <MetricItem label="xG 主" value={fmt(mc.xgHome)} highlight />
          <MetricItem label="xG 客" value={fmt(mc.xgAway)} highlight />
          {mc.xgTotal != null && <MetricItem label="总" value={fmt(mc.xgTotal)} />}
        </div>
      )}

      {/* 胜平负 + 分歧对比 */}
      <table style={{ borderCollapse: "collapse", fontSize: 12, marginBottom: 8 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", fontSize: 11, fontWeight: 400, color: "var(--text-muted)", width: 52, paddingBottom: 3 }} />
            <th style={{ ...valStyle, fontWeight: 600, color: "var(--accent)", paddingBottom: 3 }}>蒙特卡洛</th>
            {prob && <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 3 }}>OA 模型</th>}
            {prob && <th style={{ textAlign: "left", paddingLeft: 8, paddingBottom: 3, fontSize: 11, color: "var(--text-muted)", fontWeight: 400 }}>分歧</th>}
          </tr>
        </thead>
        <tbody>
          {pRows.map(({ label, sim, model }) => {
            if (sim == null && model == null) return null;
            const diff = sim != null && model != null ? Math.abs(sim - model) : null;
            const highDiv = diff != null && diff >= DIVERGE_THRESHOLD;
            return (
              <tr key={label}>
                <td style={{ fontSize: 11, color: "var(--text-muted)", paddingBottom: 2 }}>{label}</td>
                <td style={{ ...valStyle, color: "var(--text)", fontWeight: 600 }}>
                  {sim != null ? sim.toFixed(1) + "%" : "—"}
                </td>
                {prob && (
                  <td style={{ ...valStyle, color: "var(--text-secondary)" }}>
                    {model != null ? fmtPct(model) : "—"}
                  </td>
                )}
                {prob && (
                  <td style={{ paddingLeft: 8, fontSize: 11, color: highDiv ? "#ef4444" : "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    {diff != null ? (highDiv ? `⚠ ${diff.toFixed(1)}%` : diff.toFixed(1) + "%") : ""}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* 半场 */}
      {mc.firstHalf && (mc.firstHalf.home != null || mc.firstHalf.draw != null) && (
        <div style={{ display: "flex", gap: 16, marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>半场</span>
          {mc.firstHalf.home != null && <MetricItem label="主" value={mc.firstHalf.home.toFixed(1) + "%"} />}
          {mc.firstHalf.draw != null && <MetricItem label="平" value={mc.firstHalf.draw.toFixed(1) + "%"} />}
          {mc.firstHalf.away != null && <MetricItem label="客" value={mc.firstHalf.away.toFixed(1) + "%"} />}
        </div>
      )}

      {/* 高概率比分 */}
      {mc.topScorelines.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>高概率比分</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
            {mc.topScorelines.map(({ score, pct }) => (
              <span key={score} style={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--text)" }}>{score}</span>
                <span style={{ color: "var(--text-muted)", marginLeft: 3 }}>{pct.toFixed(1)}%</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </CollapsibleSection>
  );
}

// ─── H2H display ──────────────────────────────────────────────────────────────

function H2HSection({ records, homeTeam, awayTeam }: {
  records: H2HRecord[]; homeTeam: string; awayTeam: string;
}) {
  if (!records.length) return null;

  const homeWins = records.filter((r) => r.result === "home").length;
  const draws    = records.filter((r) => r.result === "draw").length;
  const awayWins = records.filter((r) => r.result === "away").length;
  const bttsCount = records.filter((r) => r.btts).length;
  const over25Count = records.filter((r) => r.over25).length;
  const n = records.length;

  return (
    <CollapsibleSection title={`H2H 历史（近 ${n} 场）`}>

      {/* Summary */}
      <div style={{ display: "flex", gap: 20, marginBottom: 8, flexWrap: "wrap" }}>
        <MetricItem
          label={`${homeTeam || "主"} 胜`}
          value={`${homeWins}/${n}`}
          highlight={homeWins > awayWins}
        />
        <MetricItem label="平" value={`${draws}/${n}`} />
        <MetricItem
          label={`${awayTeam || "客"} 胜`}
          value={`${awayWins}/${n}`}
          highlight={awayWins > homeWins}
        />
        <MetricItem label="BTTS" value={`${bttsCount}/${n} (${Math.round(bttsCount/n*100)}%)`} />
        <MetricItem label="大2.5" value={`${over25Count}/${n} (${Math.round(over25Count/n*100)}%)`} />
      </div>

      {/* Match list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
        {records.map((r, i) => {
          const resultColor = r.result === "home" ? "var(--accent)" : r.result === "away" ? "#3b82f6" : "var(--text-muted)";
          const resultLabel = r.result === "home" ? "主胜" : r.result === "away" ? "客胜" : "平局";
          const dateStr = r.date ? (String(r.date).length > 10 ? String(r.date).slice(0, 10) : String(r.date)) : "";
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 8,
              fontSize: 12, color: "var(--text-secondary)",
              padding: "4px 0",
              borderBottom: "1px solid var(--border-subtle)",
            }}>
              <span style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)", fontSize: 11, flexShrink: 0, width: 66 }}>
                {dateStr}
              </span>
              <span style={{ flex: 1, textAlign: "right", fontSize: 11 }}>{r.homeName}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, color: "var(--text)", flexShrink: 0, minWidth: 34, textAlign: "center", fontSize: 13 }}>
                {r.homeGoals}-{r.awayGoals}
              </span>
              <span style={{ flex: 1, fontSize: 11 }}>{r.awayName}</span>
              <span style={{ fontSize: 11, color: resultColor, flexShrink: 0, width: 30, textAlign: "right" }}>{resultLabel}</span>
              <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0, width: 24 }}>
                {r.btts ? "双" : ""}{r.over25 ? "大" : ""}
              </span>
            </div>
          );
        })}
      </div>
    </CollapsibleSection>
  );
}

// ─── Recent form display ──────────────────────────────────────────────────────

function RecentFormSection({ form, homeTeam, awayTeam }: {
  form: RecentFormStats; homeTeam: string; awayTeam: string;
}) {
  const home = form.home5h;
  const away = form.away5a;
  if (!home && !away) return null;

  const rows: Array<{ label: string; hVal: number | null; aVal: number | null; pct?: boolean; d?: number }> = [
    { label: "场均进球", hVal: home?.goalsForAvg ?? null,     aVal: away?.goalsForAvg ?? null },
    { label: "场均失球", hVal: home?.goalsAgainstAvg ?? null, aVal: away?.goalsAgainstAvg ?? null },
    { label: "xG 进攻",  hVal: home?.xgFor ?? null,          aVal: away?.xgFor ?? null },
    { label: "BTTS",    hVal: home?.btts ?? null,            aVal: away?.btts ?? null,   pct: true, d: 0 },
    { label: "大2.5",   hVal: home?.over25 ?? null,          aVal: away?.over25 ?? null, pct: true, d: 0 },
    { label: "零封率",  hVal: home?.cleanSheet ?? null,      aVal: away?.cleanSheet ?? null, pct: true, d: 0 },
    { label: "未进球",  hVal: home?.failedToScore ?? null,   aVal: away?.failedToScore ?? null, pct: true, d: 0 },
  ];

  const homeLabel = home?.name || homeTeam || "主队";
  const awayLabel = away?.name || awayTeam || "客队";
  const homePlayed = (home as Record<string, unknown> | null)?.played;
  const awayPlayed = (away as Record<string, unknown> | null)?.played;
  const homeCnt = homePlayed && typeof homePlayed === "object"
    ? (homePlayed as Record<string, unknown>).total ?? "" : "";
  const awayCnt = awayPlayed && typeof awayPlayed === "object"
    ? (awayPlayed as Record<string, unknown>).total ?? "" : "";

  const valStyle: CSSProperties = {
    fontFamily: "var(--font-mono)", fontSize: 12, textAlign: "right", paddingLeft: 12,
  };

  return (
    <CollapsibleSection title={`近期状态（主 ${homeCnt ? `近${homeCnt}场主场` : "主场"} / 客 ${awayCnt ? `近${awayCnt}场客场` : "客场"}）`}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left", fontSize: 11, fontWeight: 400, color: "var(--text-muted)", paddingBottom: 4, width: 76 }} />
            <th style={{ ...valStyle, fontWeight: 600, color: "var(--text)", paddingBottom: 4 }}>{homeLabel}</th>
            <th style={{ ...valStyle, fontWeight: 400, color: "var(--text-secondary)", paddingBottom: 4 }}>{awayLabel}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ label, hVal, aVal, pct, d = 2 }) => {
            if (hVal == null && aVal == null) return null;
            const fmtVal = (v: number | null) =>
              v == null ? "—" : pct ? v.toFixed(d) + "%" : v.toFixed(d);
            const higherIsBetter = !label.includes("失球") && !label.includes("未进球");
            const hWin = hVal != null && aVal != null && (higherIsBetter ? hVal > aVal : hVal < aVal);
            const aWin = hVal != null && aVal != null && (higherIsBetter ? aVal > hVal : aVal < hVal);
            return (
              <tr key={label}>
                <td style={{ fontSize: 11, color: "var(--text-muted)", paddingBottom: 2 }}>{label}</td>
                <td style={{ ...valStyle, color: hWin ? "var(--accent)" : "var(--text-secondary)", fontWeight: hWin ? 600 : 400 }}>
                  {fmtVal(hVal)}
                </td>
                <td style={{ ...valStyle, color: aWin ? "var(--accent)" : "var(--text-muted)", fontWeight: aWin ? 600 : 400 }}>
                  {fmtVal(aVal)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </CollapsibleSection>
  );
}

// ─── OddalertsMetrics ─────────────────────────────────────────────────────────

export function OddalertsMetrics({ data, homeTeam, awayTeam }: {
  data: Record<string, unknown>; homeTeam: string; awayTeam: string;
}) {
  const parsed = extractOddalertsData(data);
  const { ftOdds, ahOdds, glOdds, homeStats, awayStats, probability,
          monteCarlo, h2h, recentForm, hasEmptyOdds } = parsed;

  const hasContent = ftOdds || ahOdds || glOdds || homeStats || awayStats
    || probability || monteCarlo || h2h.length || recentForm;
  if (!hasContent) {
    return (
      <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
        {hasEmptyOdds ? "暂无赔率数据（fixture_id 可能不匹配）" : "暂无数据"}
      </span>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>

      {/* 1X2 */}
      {ftOdds && <FtOddsRow odds={ftOdds} />}

      {/* 亚盘 */}
      {ahOdds && (
        <div>
          <SectionLabel>亚盘 · Pinnacle · 让球 {ahOdds.line}</SectionLabel>
          <OddsCompactRow
            label="收盘" homeOpen={ahOdds.homeOpen} homeNow={ahOdds.homeNow}
            awayOpen={ahOdds.awayOpen} awayNow={ahOdds.awayNow}
            midLabel={`让 ${ahOdds.line}`}
          />
        </div>
      )}

      {/* 大小球 */}
      {glOdds && (
        <div>
          <SectionLabel>大小球 · Pinnacle · 盘口 {glOdds.line}</SectionLabel>
          <OddsCompactRow
            label="收盘" homeOpen={glOdds.overOpen} homeNow={glOdds.overNow}
            awayOpen={glOdds.underOpen} awayNow={glOdds.underNow}
            midLabel={glOdds.line} sideLabel="大"
          />
        </div>
      )}

      {/* Monte Carlo */}
      {monteCarlo && <MonteCarloSection mc={monteCarlo} prob={probability} />}

      {/* H2H */}
      {h2h.length > 0 && <H2HSection records={h2h} homeTeam={homeTeam} awayTeam={awayTeam} />}

      {/* 近期状态 */}
      {recentForm && <RecentFormSection form={recentForm} homeTeam={homeTeam} awayTeam={awayTeam} />}

      {/* 赛季整体统计（作为参考） */}
      {(homeStats || awayStats) && (
        <TeamStatsTable home={homeStats} away={awayStats} homeTeam={homeTeam} awayTeam={awayTeam} />
      )}

      {/* OA 概率模型（无 Monte Carlo 时单独显示，有 Monte Carlo 时已在对比表中显示）*/}
      {probability && !monteCarlo && (
        <div>
          <SectionLabel>OA 概率模型</SectionLabel>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 20px" }}>
            {probability.home_win != null && (
              <MetricItem label="主胜" value={fmtPct(probability.home_win)} highlight={(probability.home_win ?? 0) > (probability.away_win ?? 0)} />
            )}
            {probability.draw != null && (
              <MetricItem label="平" value={fmtPct(probability.draw)} />
            )}
            {probability.away_win != null && (
              <MetricItem label="客胜" value={fmtPct(probability.away_win)} highlight={(probability.away_win ?? 0) > (probability.home_win ?? 0)} />
            )}
            {probability.btts != null && (
              <MetricItem label="BTTS" value={fmtPct(probability.btts)} />
            )}
            {probability.o25 != null && (
              <MetricItem label="大2.5" value={fmtPct(probability.o25)} />
            )}
          </div>
        </div>
      )}
    </div>
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
      background: "var(--bg)",
      borderBottom: "2px solid var(--border)",
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {existingSources.map((source) => {
          const srcData = rawData![source];
          const meta = srcData._meta as Record<string, unknown> | undefined;
          return (
            <SourceCard
              key={source}
              title={SOURCE_LABELS[source] ?? source}
              icon={SOURCE_ICONS[source] ?? "🔌"}
              collectedAt={meta?.collected_at as string | undefined}
              onViewRaw={() => onViewRaw(`${SOURCE_LABELS[source] ?? source} (raw_data.${source})`, srcData)}
              onRefresh={matchId ? () => onRefresh(matchId, source) : undefined}
              refreshing={refreshingSource === source}
              refreshDisabled={!SOURCE_CAN_REFRESH.has(source)}
              refreshDisabledTip={`${SOURCE_LABELS[source] ?? source} 数据通过流水线自动更新`}
            >
              {source === "sportmonks" && <SportmonksMetrics data={srcData} homeTeam={homeTeam} awayTeam={awayTeam} />}
              {source === "oddalerts" && <OddalertsMetrics data={srcData} homeTeam={homeTeam} awayTeam={awayTeam} />}
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
      background: "var(--bg)",
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
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {(homeXg != null || awayXg != null) && (
        <MetricItem label="xG" value={`主 ${fmt(homeXg)} | 客 ${fmt(awayXg)}`} highlight />
      )}
      {probs && (
        <MetricItem
          label="胜平负"
          value={`主 ${fmtPct(probs.home_win)} | 平 ${fmtPct(probs.draw)} | 客 ${fmtPct(probs.away_win)}`}
        />
      )}
      <div style={{ display: "flex", gap: 24 }}>
        {rec && <MetricItem label="推荐" value={rec} highlight />}
        {ev != null && (
          <MetricItem label="EV" value={`${ev >= 0 ? "+" : ""}${ev.toFixed(3)}`} highlight={ev > 0.05} />
        )}
        {confidence != null && (
          <MetricItem label="置信度" value={`${(confidence * 100).toFixed(1)}%`} />
        )}
      </div>
    </div>
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
      background: "var(--bg)",
      borderBottom: "2px solid var(--border)",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      {/* Analysis summary from pipeline */}
      <SourceCard title="流水线分析" icon="🧠">
        <AnalysisMetrics record={pipelineSummary} />
      </SourceCard>

      {/* Raw data sources */}
      {existingSources.map((source) => {
        const srcData = rawData![source];
        const meta = srcData._meta as Record<string, unknown> | undefined;
        return (
          <SourceCard
            key={source}
            title={SOURCE_LABELS[source] ?? source}
            icon={SOURCE_ICONS[source] ?? "🔌"}
            collectedAt={meta?.collected_at as string | undefined}
            onViewRaw={() => onViewRaw(`${SOURCE_LABELS[source] ?? source} (raw_data.${source})`, srcData)}
            onRefresh={matchId ? () => onRefresh(matchId, source) : undefined}
            refreshing={refreshingSource === source}
            refreshDisabled={!SOURCE_CAN_REFRESH.has(source)}
            refreshDisabledTip={`${SOURCE_LABELS[source] ?? source} 数据通过流水线自动更新`}
          >
            {source === "sportmonks" && <SportmonksMetrics data={srcData} homeTeam={homeTeam} awayTeam={awayTeam} />}
            {source === "oddalerts" && <OddalertsMetrics data={srcData} homeTeam={homeTeam} awayTeam={awayTeam} />}
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
