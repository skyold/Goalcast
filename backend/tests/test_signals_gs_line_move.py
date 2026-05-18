"""GS-LineMove signal — Pinnacle 1X2 odds drift across snapshot waypoints.

The signal answers: "by how much has the market moved this match's odds
since opening?". It compares the earliest captured waypoint (typically 48h)
with the current waypoint, picking the 1X2 selection with the largest |Δ%|.

Line drifting down on one side (e.g. home 2.50 → 2.10) means the market
gained confidence in that outcome; drifting up means the opposite. The sign
carries information.
"""
from __future__ import annotations

import json

import aiosqlite
import pytest


NOW = "2026-05-18T10:00:00"


@pytest.fixture
async def db(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database
    importlib.reload(database)
    await database.init_db()

    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (10, 100, 'L', 'A', 'B', '2026-05-18T15:00:00', 'NS', ?, ?)""",
            (NOW, NOW),
        )
        for wp, oh, od, oa in [("48h", 2.50, 3.20, 3.00),
                               ("24h", 2.30, 3.30, 3.10),
                               ("1h",  2.10, 3.40, 3.20)]:
            for outcome, odds in (("home", oh), ("draw", od), ("away", oa)):
                await conn.execute(
                    """INSERT INTO historical_odds
                       (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                       VALUES (10, 1, 6, ?, ?, ?, ?)""",
                    (outcome, wp, odds, NOW),
                )
        await conn.commit()

    conn = await aiosqlite.connect(str(tmp_path / "test.db"))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_line_move_picks_max_abs_pct_drift(db):
    """home: (2.10-2.50)/2.50 = -16.0%  ← largest |Δ|
       draw: (3.40-3.20)/3.20 ≈ +6.25%
       away: (3.20-3.00)/3.00 ≈ +6.67%
       → selection='home', move_pct=-16.0, strength=0.80 (|move|/20 capped)."""
    from services.signals.gs_line_move import GSLineMove
    result = await GSLineMove().compute(db, fixture_id=10, waypoint="1h")
    assert result is not None
    v = json.loads(result["value_json"])
    assert v["selection"] == "home"
    assert v["move_pct"] == pytest.approx(-16.0, abs=0.05)
    assert v["open_odds"] == pytest.approx(2.50)
    assert v["current_odds"] == pytest.approx(2.10)
    assert result["strength"] == pytest.approx(0.80, abs=0.005)


@pytest.mark.asyncio
async def test_line_move_returns_none_at_first_waypoint(db, tmp_path):
    """First waypoint ever captured — no earlier point to compare with."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE waypoint != '48h'")
        await conn.commit()
    from services.signals.gs_line_move import GSLineMove
    result = await GSLineMove().compute(db, fixture_id=10, waypoint="48h")
    assert result is None


@pytest.mark.asyncio
async def test_line_move_returns_none_when_outcomes_incomplete(db, tmp_path):
    """Need all three 1X2 outcomes on both endpoints."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            "DELETE FROM historical_odds WHERE fixture_id=10 AND outcome='draw'"
        )
        await conn.commit()
    from services.signals.gs_line_move import GSLineMove
    result = await GSLineMove().compute(db, fixture_id=10, waypoint="1h")
    assert result is None


@pytest.mark.asyncio
async def test_line_move_metadata(db):
    from services.signals.gs_line_move import GSLineMove
    s = GSLineMove()
    assert s.signal_type == "GS-LineMove"
    assert s.signal_version == "v1.0"
    assert s.scope == "member"
