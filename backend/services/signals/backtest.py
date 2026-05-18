"""Signal-layer backtest — historical replay of (signal × conditions) against
realised FT outcomes, producing the same ROI / hit-rate / equity curve metrics
the live snapshot worker will produce going forward (forward + backtest share
`services.signals.conditions.eval_conditions`).

Scope (V1.5, per PRD signal-catalog-and-subscriptions § Phase 3):
  - Only 1X2 signals whose `value.selection ∈ {home, draw, away}` are
    settleable here. HT-EV is excluded — it bets the HT-draw AH market,
    which needs HT scores + AH market_id=51 odds that the current snapshot
    pipeline doesn't capture. (Documented as Phase 3 Won't in PRD.)
  - Pinnacle 1X2 (bookmaker_id=1, market_id=6) is the settlement book.
  - Stake fixed at 1 unit per signal (consistent with paper-trading V1).
  - match_scope='my_leagues' filters by user's user_competition_prefs.
"""
from __future__ import annotations

import json
from typing import Literal, TypedDict

import aiosqlite


Window = Literal["7d", "14d", "30d"]
MatchScope = Literal["all", "my_leagues"]

_DAYS_BY_WINDOW: dict[Window, int] = {"7d": 7, "14d": 14, "30d": 30}
_VALID_SELECTIONS = {"home", "draw", "away"}


class EquityPoint(TypedDict):
    date: str           # YYYY-MM-DD (UTC), kickoff date of the settling fixture
    cum_pnl: float      # cumulative profit/loss in units after this fixture


class BacktestResult(TypedDict):
    signal_type:      str
    window:           Window
    match_scope:      MatchScope
    considered_count: int
    settled_count:    int
    roi_pct:          float | None
    hit_rate:         float | None
    max_drawdown_pct: float | None
    equity_curve:     list[EquityPoint]


def _outcome_won(selection: str, score_home: int | None, score_away: int | None) -> bool | None:
    """Return whether the chosen 1X2 selection won. None if scores unavailable."""
    if score_home is None or score_away is None:
        return None
    if selection == "home": return score_home > score_away
    if selection == "away": return score_away > score_home
    if selection == "draw": return score_home == score_away
    return None


async def run_backtest(
    db: aiosqlite.Connection,
    *,
    signal_type: str,
    conditions: dict,
    window: Window = "30d",
    match_scope: MatchScope = "all",
    user_id: int | None = None,
) -> BacktestResult:
    """Replay historical signals_snapshot rows against FT outcomes."""
    from services.signals.conditions import eval_conditions

    days = _DAYS_BY_WINDOW[window]
    # signals_snapshot × fixtures(FT) within window.
    sql = """
        SELECT s.fixture_id, s.waypoint, s.value_json, s.strength,
               f.kickoff_utc, f.score_home, f.score_away, f.competition_id
        FROM signals_snapshot s
        JOIN fixtures f ON f.id = s.fixture_id
        WHERE s.signal_type = ?
          AND s.captured_at >= datetime('now', ?)
          AND f.status = 'FT'
    """
    params: list = [signal_type, f"-{days} days"]

    if match_scope == "my_leagues":
        if user_id is None:
            # No user → return empty result (handler is responsible for catching
            # this earlier; defensive here).
            return _empty_result(signal_type, window, match_scope)
        sql += """
          AND EXISTS (
            SELECT 1 FROM user_competition_prefs p
            WHERE p.user_id = ? AND p.competition_id = f.competition_id
          )
        """
        params.append(user_id)

    sql += " ORDER BY f.kickoff_utc ASC"

    async with db.execute(sql, params) as cur:
        snapshot_rows = [dict(r) for r in await cur.fetchall()]

    considered_count = len(snapshot_rows)
    if not snapshot_rows:
        return _empty_result(signal_type, window, match_scope)

    # Pre-fetch Pinnacle 1X2 odds for all (fixture, waypoint) combos involved.
    # SQLite has no array params, so build placeholders. Limit at ~999 placeholders
    # per IN clause — our windows are small (≤ 30 days, ≤ a few hundred fixtures
    # × few waypoints) so this is fine.
    pairs = {(r["fixture_id"], r["waypoint"]) for r in snapshot_rows}
    placeholders = ",".join("(?,?)" for _ in pairs)
    flat: list = []
    for fid, wp in pairs:
        flat.extend([fid, wp])
    odds_sql = f"""
        SELECT fixture_id, waypoint, outcome, odds
        FROM historical_odds
        WHERE bookmaker_id = 1 AND market_id = 6
          AND outcome IN ('home','draw','away')
          AND (fixture_id, waypoint) IN (VALUES {placeholders})
    """
    async with db.execute(odds_sql, flat) as cur:
        odds_rows = await cur.fetchall()
    # (fixture_id, waypoint) → {outcome: odds}
    odds_idx: dict[tuple[int, str], dict[str, float]] = {}
    for r in odds_rows:
        key = (r["fixture_id"], r["waypoint"])
        odds_idx.setdefault(key, {})[r["outcome"]] = float(r["odds"])

    # Walk snapshots in kickoff order, settle each that passes conditions and
    # has the required odds, accumulating equity curve.
    cum_pnl = 0.0
    wins = 0
    settled = 0
    peak = 0.0
    max_dd = 0.0
    points: list[EquityPoint] = []

    for r in snapshot_rows:
        # Conditions evaluator works on the same shape as live signal results.
        signal_result = {"strength": r["strength"], "value_json": r["value_json"]}
        if not eval_conditions(conditions, signal_result):
            continue
        try:
            value = json.loads(r["value_json"]) if r["value_json"] else {}
        except (TypeError, ValueError):
            continue
        sel = value.get("selection")
        if sel not in _VALID_SELECTIONS:
            continue  # non-1X2 signals (e.g. GS-KEN-HT-EV) → unsettleable here
        odds_for = odds_idx.get((r["fixture_id"], r["waypoint"]), {})
        odds = odds_for.get(sel)
        if not odds or odds <= 0:
            continue
        won = _outcome_won(sel, r["score_home"], r["score_away"])
        if won is None:
            continue
        pnl = (odds - 1.0) if won else -1.0
        cum_pnl += pnl
        settled += 1
        if won:
            wins += 1
        peak = max(peak, cum_pnl)
        dd = peak - cum_pnl
        max_dd = max(max_dd, dd)
        date_str = (r["kickoff_utc"] or "")[:10]  # YYYY-MM-DD
        points.append({"date": date_str, "cum_pnl": round(cum_pnl, 2)})

    if settled == 0:
        return {
            "signal_type":      signal_type,
            "window":           window,
            "match_scope":      match_scope,
            "considered_count": considered_count,
            "settled_count":    0,
            "roi_pct":          None,
            "hit_rate":         None,
            "max_drawdown_pct": None,
            "equity_curve":     [],
        }

    # ROI = cum_pnl / total_stake.  stake = 1 unit per bet → total_stake = settled.
    roi_pct = round(cum_pnl / settled * 100.0, 2)
    hit_rate = round(wins / settled, 4)
    # max_drawdown_pct expressed as % of total stake invested (settled units).
    max_dd_pct = round(max_dd / settled * 100.0, 2) if settled > 0 else 0.0

    return {
        "signal_type":      signal_type,
        "window":           window,
        "match_scope":      match_scope,
        "considered_count": considered_count,
        "settled_count":    settled,
        "roi_pct":          roi_pct,
        "hit_rate":         hit_rate,
        "max_drawdown_pct": max_dd_pct,
        "equity_curve":     points,
    }


def _empty_result(signal_type: str, window: Window, match_scope: MatchScope) -> BacktestResult:
    return {
        "signal_type":      signal_type,
        "window":           window,
        "match_scope":      match_scope,
        "considered_count": 0,
        "settled_count":    0,
        "roi_pct":          None,
        "hit_rate":         None,
        "max_drawdown_pct": None,
        "equity_curve":     [],
    }
