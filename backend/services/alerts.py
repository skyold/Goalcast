"""Phase 3 — Sharp vs Square 分歧告警扫描.

Pinnacle (bookmaker_id=1) is the sharp; Bet365 (bookmaker_id=2) is the square.
For each upcoming fixture in [now, now+24h] we compute de-vigged implied
probabilities for both books on the 1x2 market (market_id=6) and emit an alert
when the maximum |delta| over the 3 outcomes exceeds the user's threshold
(default 5%). 30-min dedupe window per (user, fixture) prevents spam from a
threshold that stays satisfied across consecutive scans.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite

ALERT_TYPE_DIVERGENCE = "sharp_square_divergence"


def compute_divergence(
    pinnacle: dict[str, float],
    bet365: dict[str, float],
) -> dict:
    """Return per-outcome implied probabilities for each book (de-vigged) plus
    the max |delta_pct| across {home, draw, away}.

    Inputs are dicts shaped {'home': odds, 'draw': odds, 'away': odds}.
    Raises ValueError if any odds are missing or non-positive.
    """
    def implied_devigged(odds: dict[str, float]) -> dict[str, float]:
        if any(o is None or o <= 0 for o in odds.values()):
            raise ValueError(f"invalid odds: {odds}")
        raw = {k: 1.0 / v for k, v in odds.items()}
        s = sum(raw.values())
        return {k: r / s for k, r in raw.items()}

    pin_imp = implied_devigged(pinnacle)
    bk_imp = implied_devigged(bet365)
    deltas = {k: (bk_imp[k] - pin_imp[k]) * 100.0 for k in pin_imp}
    max_outcome, max_delta = max(deltas.items(), key=lambda kv: abs(kv[1]))
    return {
        "pinnacle_implied": pin_imp,
        "bet365_implied": bk_imp,
        "deltas_pct": deltas,
        "max_outcome": max_outcome,
        "max_delta_pct": max_delta,
    }


async def scan_alerts(db: aiosqlite.Connection, *, now: Optional[datetime] = None, dedupe_minutes: int = 30) -> int:
    """One-shot scan. Returns number of inserted alert rows."""
    now = now or datetime.now(timezone.utc)
    cutoff = (now + timedelta(hours=24)).isoformat()
    dedupe_cutoff = (now - timedelta(minutes=dedupe_minutes)).isoformat()

    # 1. Pull every NS fixture in the next 24h that has both Pinnacle and Bet365
    #    1x2 odds across all 3 outcomes. We pivot the bookmaker_odds rows into
    #    one row per fixture via subqueries.
    sql = """
      WITH fx AS (
        SELECT f.id, f.kickoff_utc, f.competition_id
        FROM fixtures f
        WHERE f.status='NS' AND f.kickoff_utc >= ? AND f.kickoff_utc <= ?
      )
      SELECT fx.id, fx.kickoff_utc, fx.competition_id,
             pin_h.current AS pin_h, pin_d.current AS pin_d, pin_a.current AS pin_a,
             b_h.current   AS b_h,   b_d.current   AS b_d,   b_a.current   AS b_a
      FROM fx
      JOIN bookmaker_odds pin_h ON pin_h.fixture_id=fx.id AND pin_h.bookmaker_id=1 AND pin_h.market_id=6 AND pin_h.outcome='home'
      JOIN bookmaker_odds pin_d ON pin_d.fixture_id=fx.id AND pin_d.bookmaker_id=1 AND pin_d.market_id=6 AND pin_d.outcome='draw'
      JOIN bookmaker_odds pin_a ON pin_a.fixture_id=fx.id AND pin_a.bookmaker_id=1 AND pin_a.market_id=6 AND pin_a.outcome='away'
      JOIN bookmaker_odds b_h   ON b_h.fixture_id=fx.id   AND b_h.bookmaker_id=2   AND b_h.market_id=6   AND b_h.outcome='home'
      JOIN bookmaker_odds b_d   ON b_d.fixture_id=fx.id   AND b_d.bookmaker_id=2   AND b_d.market_id=6   AND b_d.outcome='draw'
      JOIN bookmaker_odds b_a   ON b_a.fixture_id=fx.id   AND b_a.bookmaker_id=2   AND b_a.market_id=6   AND b_a.outcome='away'
    """
    async with db.execute(sql, (now.isoformat(), cutoff)) as cur:
        fixtures = [dict(r) for r in await cur.fetchall()]

    # 2. Pull enabled users + threshold (defaulting to 5.0 when row missing).
    async with db.execute(
        """SELECT u.id AS user_id,
                  COALESCE(s.divergence_threshold, 5.0) AS threshold,
                  COALESCE(s.enabled, 1) AS enabled
           FROM users u
           LEFT JOIN user_alert_settings s ON s.user_id = u.id"""
    ) as cur:
        users = [dict(r) for r in await cur.fetchall() if r["enabled"]]

    # 3. Pull each user's pref set (one query, group in Python).
    async with db.execute("SELECT user_id, competition_id FROM user_competition_prefs") as cur:
        prefs: dict[int, set[int]] = {}
        for r in await cur.fetchall():
            prefs.setdefault(r["user_id"], set()).add(r["competition_id"])

    inserted = 0
    for fx in fixtures:
        try:
            div = compute_divergence(
                {"home": fx["pin_h"], "draw": fx["pin_d"], "away": fx["pin_a"]},
                {"home": fx["b_h"],   "draw": fx["b_d"],   "away": fx["b_a"]},
            )
        except ValueError:
            continue
        max_abs = abs(div["max_delta_pct"])

        for u in users:
            if max_abs < u["threshold"]:
                continue
            user_prefs = prefs.get(u["user_id"], set())
            # Empty prefs = no alerts (consistent with PRD: alerts only on My Leagues).
            if not user_prefs or fx["competition_id"] not in user_prefs:
                continue

            # 30-min dedupe per (user, fixture).
            async with db.execute(
                """SELECT 1 FROM alerts
                   WHERE user_id=? AND fixture_id=? AND alert_type=?
                     AND datetime(created_at) >= datetime(?)
                   LIMIT 1""",
                (u["user_id"], fx["id"], ALERT_TYPE_DIVERGENCE, dedupe_cutoff),
            ) as ck:
                if await ck.fetchone():
                    continue

            payload = json.dumps({
                "pinnacle_odds": {"home": fx["pin_h"], "draw": fx["pin_d"], "away": fx["pin_a"]},
                "bet365_odds":   {"home": fx["b_h"],   "draw": fx["b_d"],   "away": fx["b_a"]},
                "pinnacle_implied_pct": {k: round(v * 100, 2) for k, v in div["pinnacle_implied"].items()},
                "bet365_implied_pct":   {k: round(v * 100, 2) for k, v in div["bet365_implied"].items()},
                "max_outcome": div["max_outcome"],
                "max_delta_pct": round(div["max_delta_pct"], 2),
            })
            kickoff_dt = datetime.fromisoformat(fx["kickoff_utc"].replace("Z", "+00:00"))
            if kickoff_dt.tzinfo is None:
                kickoff_dt = kickoff_dt.replace(tzinfo=timezone.utc)
            expires_at = (kickoff_dt + timedelta(minutes=30)).isoformat()

            await db.execute(
                """INSERT INTO alerts (user_id, fixture_id, alert_type, payload, expires_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (u["user_id"], fx["id"], ALERT_TYPE_DIVERGENCE, payload, expires_at),
            )
            inserted += 1

    if inserted:
        await db.commit()
    return inserted
