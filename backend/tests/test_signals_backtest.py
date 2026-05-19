"""Integration tests for services.signals.backtest.run_backtest.

Seeds a small synthetic universe of signals_snapshot × fixtures(FT) × Pinnacle
historical_odds, exercises various conditions / windows / match_scopes, and
checks settlement arithmetic (ROI, hit rate, drawdown, equity curve order).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import aiosqlite
import pytest

from services.signals.backtest import run_backtest


# Use `now` minus offsets so we land inside the SQLite "now - N days" window.
NOW = datetime.now(timezone.utc)


def _ago(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat()


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database
    importlib.reload(database)
    await database.init_db()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        conn.row_factory = aiosqlite.Row
        # 3 FT fixtures inside 30d window + 1 outside (40d old).
        # Fixture 10 (3 days ago): home wins 2-0, in competition 100
        # Fixture 11 (5 days ago): away wins 0-1, in competition 100
        # Fixture 12 (10 days ago): draw 1-1, in competition 200
        # Fixture 13 (40 days ago): home wins 3-1, in competition 100 (outside)
        seed_fixtures = [
            (10, 100, "L1", 1, 2, "home", "away", 2, 0,         _ago(3)),
            (11, 100, "L1", 3, 4, "home", "away", 0, 1,         _ago(5)),
            (12, 200, "L2", 5, 6, "home", "away", 1, 1,         _ago(10)),
            (13, 100, "L1", 7, 8, "home", "away", 3, 1,         _ago(40)),
        ]
        for fid, cid, cname, hid, aid, ht, at, sh, sa, ko in seed_fixtures:
            await conn.execute(
                """INSERT INTO fixtures (id, competition_id, competition_name,
                   home_team, away_team, home_team_id, away_team_id,
                   kickoff_utc, status, score_home, score_away, fetched_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,'FT',?,?,?,?)""",
                (fid, cid, cname, ht, at, hid, aid, ko, sh, sa, ko, ko),
            )
        # Pinnacle 1X2 odds at 'kickoff' waypoint for each fixture.
        # Picked so the home-pick wins +1.0 for fid 10 (odds 2.00 → +1.0),
        # away-pick wins +2.0 for fid 11 (odds 3.00),
        # draw-pick wins +2.4 for fid 12 (odds 3.40).
        for fid, oh, od, oa in [
            (10, 2.00, 3.50, 4.00),
            (11, 1.80, 3.40, 3.00),
            (12, 2.50, 3.40, 2.80),
            (13, 1.95, 3.40, 4.20),
        ]:
            for outcome, odd in (("home", oh), ("draw", od), ("away", oa)):
                await conn.execute(
                    """INSERT INTO historical_odds
                       (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                       VALUES (?, 1, 6, ?, 'kickoff', ?, ?)""",
                    (fid, outcome, odd, _ago(3)),
                )
        # signals_snapshot rows for GS-Mispricing.
        snapshots = [
            (10, "GS-Mispricing", "kickoff", 0.80, "home", _ago(3)),  # win  → +1.00
            (11, "GS-Mispricing", "kickoff", 0.70, "away", _ago(5)),  # win  → +2.00
            (12, "GS-Mispricing", "kickoff", 0.60, "draw", _ago(10)), # win  → +2.40
            (13, "GS-Mispricing", "kickoff", 0.90, "home", _ago(40)), # outside 30d
        ]
        for fid, st, wp, strength, sel, captured in snapshots:
            await conn.execute(
                """INSERT INTO signals_snapshot
                   (fixture_id, signal_type, signal_version, waypoint, scope,
                    value_json, strength, captured_at)
                   VALUES (?, ?, 'v1.0', ?, 'public', ?, ?, ?)""",
                (fid, st, wp, json.dumps({"selection": sel}), strength, captured),
            )
        await conn.commit()

    conn = await aiosqlite.connect(str(tmp_path / "test.db"))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_30d_window_includes_three_fixtures(db):
    """Default empty conditions = pass all → 3 settled in 30d window."""
    r = await run_backtest(db, signal_type="GS-Mispricing", conditions={}, window="30d")
    assert r["considered_count"] == 3
    assert r["settled_count"] == 3
    # PnL: home@2.0 → +1.0; away@3.0 → +2.0; draw@3.4 → +2.4 → cum = 5.4
    # ROI = 5.4 / 3 * 100 = 180.0
    assert r["roi_pct"] == pytest.approx(180.0, abs=0.01)
    assert r["hit_rate"] == pytest.approx(1.0)
    # All 3 won → max drawdown is 0%.
    assert r["max_drawdown_pct"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_7d_window_includes_only_recent(db):
    """7d window excludes the 10-day-old fixture 12."""
    r = await run_backtest(db, signal_type="GS-Mispricing", conditions={}, window="7d")
    assert r["considered_count"] == 2  # fixtures 10 (3d) + 11 (5d)
    assert r["settled_count"] == 2


@pytest.mark.asyncio
async def test_40d_old_excluded_from_30d_window(db):
    """Fixture 13 (40 days old) not included even though it's a strong signal."""
    r = await run_backtest(db, signal_type="GS-Mispricing", conditions={}, window="30d")
    # fixture 13 would have added +0.95 to cum_pnl if included.
    # Total cum_pnl is 5.4 → check we don't see 6.35.
    assert r["equity_curve"][-1]["cum_pnl"] == pytest.approx(5.4, abs=0.01)


@pytest.mark.asyncio
async def test_strength_min_filter(db):
    """strength_min=0.75 keeps only fixture 10 (0.80)."""
    r = await run_backtest(
        db, signal_type="GS-Mispricing",
        conditions={"strength_min": 0.75}, window="30d",
    )
    assert r["settled_count"] == 1
    assert r["roi_pct"] == pytest.approx(100.0)  # +1 / 1 stake → 100%


@pytest.mark.asyncio
async def test_filter_excludes_draws(db):
    """value.selection != draw → fixture 12 dropped."""
    r = await run_backtest(
        db, signal_type="GS-Mispricing",
        conditions={"filters": [{"path": "value.selection", "op": "!=", "value": "draw"}]},
        window="30d",
    )
    assert r["settled_count"] == 2  # fixtures 10 + 11


@pytest.mark.asyncio
async def test_match_scope_my_leagues_requires_user_id(db):
    """match_scope='my_leagues' without user_id → empty result."""
    r = await run_backtest(
        db, signal_type="GS-Mispricing", conditions={},
        window="30d", match_scope="my_leagues", user_id=None,
    )
    assert r["considered_count"] == 0


@pytest.mark.asyncio
async def test_match_scope_my_leagues_filters_by_prefs(db, tmp_path):
    """user_id=1 with pref for competition 100 only → fixture 12 (comp 200) excluded."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            "INSERT INTO users (id, email, password_hash) VALUES (1, 'u@x', 'h')"
        )
        await conn.execute(
            "INSERT INTO user_competition_prefs (user_id, competition_id) VALUES (1, 100)"
        )
        await conn.commit()
    r = await run_backtest(
        db, signal_type="GS-Mispricing", conditions={},
        window="30d", match_scope="my_leagues", user_id=1,
    )
    # Fixtures 10 + 11 (comp 100) → 2 settled; fixture 12 (comp 200) excluded.
    assert r["considered_count"] == 2
    assert r["settled_count"] == 2


@pytest.mark.asyncio
async def test_equity_curve_sorted_by_kickoff(db):
    """Curve must be chronological (oldest → newest) so cum_pnl is meaningful."""
    r = await run_backtest(db, signal_type="GS-Mispricing", conditions={}, window="30d")
    dates = [p["date"] for p in r["equity_curve"]]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_returns_none_metrics_when_zero_settled(db):
    """Filter so strict nothing matches → all None metrics, empty curve."""
    r = await run_backtest(
        db, signal_type="GS-Mispricing",
        conditions={"strength_min": 0.999}, window="30d",
    )
    assert r["settled_count"] == 0
    assert r["roi_pct"] is None
    assert r["hit_rate"] is None
    assert r["max_drawdown_pct"] is None
    assert r["equity_curve"] == []


@pytest.mark.asyncio
async def test_unsettleable_non_1x2_selection_skipped(db, tmp_path):
    """A signal whose value.selection is not in {home,draw,away} cannot settle
    here. The HT-EV signal is excluded from backtest by this rule."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint, scope,
                  value_json, strength, captured_at)
               VALUES (10, 'GS-Junk', 'v1.0', 'kickoff', 'public', ?, 0.9, ?)""",
            (json.dumps({"selection": "exotic"}), _ago(3)),
        )
        await conn.commit()
    r = await run_backtest(db, signal_type="GS-Junk", conditions={}, window="30d")
    assert r["considered_count"] == 1
    assert r["settled_count"] == 0


@pytest.mark.asyncio
async def test_missing_pinnacle_odds_skipped(db, tmp_path):
    """historical_odds without Pinnacle 1X2 for this (fixture, waypoint)
    → counted as considered but not settled."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        # New fixture FT but no odds.
        await conn.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name, home_team, away_team,
                kickoff_utc, status, score_home, score_away, fetched_at, updated_at)
                VALUES (50, 100, 'L1', 'X', 'Y', ?, 'FT', 1, 0, ?, ?)""",
            (_ago(2), _ago(2), _ago(2)),
        )
        await conn.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint, scope,
                  value_json, strength, captured_at)
               VALUES (50, 'GS-Mispricing', 'v1.0', 'kickoff', 'public', ?, 0.8, ?)""",
            (json.dumps({"selection": "home"}), _ago(2)),
        )
        await conn.commit()
    r = await run_backtest(db, signal_type="GS-Mispricing", conditions={}, window="30d")
    # 3 with odds + 1 new without = 4 considered; only the 3 with odds settle.
    assert r["considered_count"] == 4
    assert r["settled_count"] == 3
