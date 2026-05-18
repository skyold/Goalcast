"""GS-SharpSquare signal — Pinnacle (sharp) vs Bet365 (square) 1X2 disagreement.

For a (fixture, waypoint) we de-vig each book's 1X2 line independently, then
take the selection with the largest |Pinnacle_pct - Bet365_pct| delta.
Positive: Pinnacle gives MORE probability than Bet365 → sharp money sides
home/draw/away vs public. Negative: opposite. Sign matters.
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
        # Pinnacle (bookmaker_id=1): 1.9/3.4/5.5 → de-vig ~ 52.51 / 29.34 / 18.14
        # Bet365   (bookmaker_id=2): 2.0/3.4/4.0 → de-vig ~ 47.89 / 28.17 / 23.94
        # Delta (Pinnacle - Bet365): home +4.62, draw +1.17, away -5.80
        # → selection='away', delta_pct=-5.80, strength=0.58.
        for bkm, (oh, od, oa) in [(1, (1.9, 3.4, 5.5)), (2, (2.0, 3.4, 4.0))]:
            for outcome, odds in (("home", oh), ("draw", od), ("away", oa)):
                await conn.execute(
                    """INSERT INTO historical_odds
                       (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                       VALUES (10, ?, 6, ?, 'kickoff', ?, ?)""",
                    (bkm, outcome, odds, NOW),
                )
        await conn.commit()

    conn = await aiosqlite.connect(str(tmp_path / "test.db"))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_sharp_square_picks_max_abs_delta(db):
    from services.signals.gs_sharp_square import GSSharpSquare
    result = await GSSharpSquare().compute(db, fixture_id=10, waypoint="kickoff")
    assert result is not None
    v = json.loads(result["value_json"])
    assert v["selection"] == "away"
    assert v["delta_pct"] == pytest.approx(-5.80, abs=0.05)
    assert v["pinnacle_pct"] == pytest.approx(18.14, abs=0.05)
    assert v["bet365_pct"]   == pytest.approx(23.94, abs=0.05)
    assert result["strength"] == pytest.approx(0.58, abs=0.005)


@pytest.mark.asyncio
async def test_sharp_square_returns_none_when_one_book_missing(db, tmp_path):
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE bookmaker_id=2")
        await conn.commit()
    from services.signals.gs_sharp_square import GSSharpSquare
    result = await GSSharpSquare().compute(db, fixture_id=10, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_sharp_square_returns_none_when_outcome_incomplete(db, tmp_path):
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        # Drop Pinnacle's draw → can't de-vig that book.
        await conn.execute(
            "DELETE FROM historical_odds WHERE bookmaker_id=1 AND outcome='draw'"
        )
        await conn.commit()
    from services.signals.gs_sharp_square import GSSharpSquare
    result = await GSSharpSquare().compute(db, fixture_id=10, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_sharp_square_metadata(db):
    from services.signals.gs_sharp_square import GSSharpSquare
    s = GSSharpSquare()
    assert s.signal_type == "GS-SharpSquare"
    assert s.signal_version == "v1.0"
    assert s.scope == "member"
