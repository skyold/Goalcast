"""GS-Mispricing signal — TDD anchor for the snapshot-driven signals pipeline.

The single critical assertion: the new GSMispricing.compute() must select the
same (selection, delta_pct) as the legacy /api/insights/mispricings dedupe
logic (commit ba27fab — "pick the selection with the largest |delta| per
fixture"). If this passes, the eventual refactor of /insights/mispricings
into a compatibility shim over GSMispricing is behavior-preserving by
construction.
"""
from __future__ import annotations

import json

import aiosqlite
import pytest


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Spin up a clean test DB with the full schema and one synthetic fixture
    plus historical_predictions + historical_odds rows at waypoint='kickoff'."""
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    import importlib, database
    importlib.reload(database)
    await database.init_db()

    now = "2026-05-18T10:00:00"
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (10, 100, 'Synthetic League', 'Alpha', 'Bravo',
                       '2026-05-18T15:00:00', 'NS', ?, ?)""",
            (now, now),
        )
        # Case mirrors list_mispricings worked example: model 70/20/10,
        # odds 1.9/3.4/5.5. Expected max |Δ| selection = 'home', delta ≈ +17.5.
        await conn.execute(
            """INSERT INTO historical_predictions
                 (fixture_id, waypoint, simulations,
                  home_win_pct, draw_pct, away_win_pct,
                  btts_pct, o25_pct, scorelines, captured_at)
               VALUES (10, 'kickoff', 100, 70.0, 20.0, 10.0, 50.0, 50.0, '{}', ?)""",
            (now,),
        )
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
               VALUES (10, 1, 6, ?, 'kickoff', ?, ?)""",
            [("home", 1.9, now), ("draw", 3.4, now), ("away", 5.5, now)],
        )
        await conn.commit()

    conn = await aiosqlite.connect(str(tmp_path / "test.db"))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_matches_legacy_dedupe_picks_max_abs_delta(db):
    """Equivalent inputs → same selection as list_mispricings (commit ba27fab).

    With model 70/20/10 and odds 1.9/3.4/5.5:
      raw_imp = 1/1.9 + 1/3.4 + 1/5.5 ≈ 1.0023
      de-vig  = 52.51 / 29.34 / 18.14
      delta   = +17.49 / -9.34 / -8.14
      max|Δ|  = home  → returned selection."""
    from services.signals.gs_mispricing import GSMispricing
    sig = GSMispricing()
    result = await sig.compute(db, fixture_id=10, waypoint="kickoff")
    assert result is not None
    value = json.loads(result["value_json"])
    assert value["selection"] == "home"
    assert value["delta_pct"] == pytest.approx(17.49, abs=0.05)
    # Strength normalization: |Δ| >= 10% caps at 1.0.
    assert result["strength"] == pytest.approx(1.0, abs=0.001)


@pytest.mark.asyncio
async def test_returns_none_when_predictions_missing(db, tmp_path):
    """Missing historical_predictions → no signal (do not coerce)."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_predictions WHERE fixture_id=10")
        await conn.commit()
    from services.signals.gs_mispricing import GSMispricing
    result = await GSMispricing().compute(db, fixture_id=10, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_odds_incomplete(db, tmp_path):
    """Missing any of 3 1X2 outcomes → no signal (de-vig requires all three)."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            "DELETE FROM historical_odds WHERE fixture_id=10 AND outcome='draw'"
        )
        await conn.commit()
    from services.signals.gs_mispricing import GSMispricing
    result = await GSMispricing().compute(db, fixture_id=10, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_signal_metadata(db):
    """Signal exposes stable type / version / scope."""
    from services.signals.gs_mispricing import GSMispricing
    sig = GSMispricing()
    assert sig.signal_type == "GS-Mispricing"
    assert sig.signal_version == "v1.0"
    assert sig.scope == "public"
