"""GS-KEN-HT-EV signal — 上半场平手盘 EV 5%~28% 反推香港盘赔率区间.

Mirrors OA_HT_V2.py (docs/OA_HT_V2.py) — but as a Pure Function on the
snapshot pipeline.

Inputs (historical_*):
- HT 1X2 probabilities from historical_predictions (home_win_ht_pct / draw_ht_pct
  / away_win_ht_pct, added via idempotent ALTER in database.py).
- FT main AH line from historical_odds (market_id=51) — BET365 (bookmaker_id=2)
  preferred, Pinnacle (1) fallback. Filter: line ∈ {0, ±0.25, ±0.5}.

Output value_json:
    {"ah_line":      float,                # FT main AH line, home perspective
     "ah_label":     "draw" | "draw_half_home" | "draw_half_away"
                                          | "half_home"      | "half_away",
     "ht_home_pct":  float, "ht_draw_pct": float, "ht_away_pct": float,
     "eff_home":     float, "eff_away":    float,  # de-vigged 2-way HT probs
     "hk_home_5":    float, "hk_home_28":  float,  # HK odds for HT draw AH home
     "hk_away_5":    float, "hk_away_28":  float,  # HK odds for HT draw AH away
     "selection":    "home" | "away"}              # higher-prob side

strength = min(2 * |eff_home - 0.5|, 1.0)  — coin flip = 0, dominant side = 1.
"""
from __future__ import annotations

import json

import aiosqlite
import pytest


@pytest.fixture
async def db(tmp_path, monkeypatch):
    """Clean DB + one fixture with HT predictions and a balanced FT-AH market."""
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
               VALUES (20, 200, 'Synthetic League', 'Alpha', 'Bravo',
                       '2026-05-18T15:00:00', 'NS', ?, ?)""",
            (now, now),
        )
        # HT 1X2 probs: home=42 / draw=28 / away=30.
        # 2-way de-vig: eff_home = 42/(42+30) = 0.5833, eff_away = 0.4167.
        await conn.execute(
            """INSERT INTO historical_predictions
                 (fixture_id, waypoint, simulations,
                  home_win_pct, draw_pct, away_win_pct,
                  home_win_ht_pct, draw_ht_pct, away_win_ht_pct,
                  btts_pct, o25_pct, scorelines, captured_at)
               VALUES (20, 'kickoff', 100, 55.0, 25.0, 20.0,
                       42.0, 28.0, 30.0, 50.0, 50.0, '{}', ?)""",
            (now,),
        )
        # Balanced FT AH from BET365 (bookmaker_id=2, market_id=51).
        # Line 0:    home_odds=1.95, away_odds=1.85 → diff=0.10 → main line.
        # Line +0.5: home_odds=2.50, away_odds=1.50 → diff=1.00 → not picked.
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 2, 51, ?, 'kickoff', ?, ?)""",
            [
                ("home_0",   1.95, now),
                ("away_0",   1.85, now),
                ("home_p05", 2.50, now),
                ("away_m05", 1.50, now),
            ],
        )
        await conn.commit()

    conn = await aiosqlite.connect(str(tmp_path / "test.db"))
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_balanced_draw_line_emits_ev_bands(db):
    """HT 42/28/30 + FT AH line=0 → author's V2 EV math (de-vigged 2-way).

    Formula (mirrors OA_HT_V2.py:281-288):
        eff_h = rH / (rH + rA)
        hk_h_ev = (ev + eff_a) / eff_h
    """
    from services.signals.gs_ht_ev import GSHtEv
    sig = GSHtEv()
    result = await sig.compute(db, fixture_id=20, waypoint="kickoff")
    assert result is not None
    v = json.loads(result["value_json"])

    assert v["ah_line"] == pytest.approx(0.0, abs=1e-6)
    assert v["ah_label"] == "draw"
    assert v["ht_home_pct"] == 42.0
    assert v["ht_draw_pct"] == 28.0
    assert v["ht_away_pct"] == 30.0

    # eff_home = 42 / (42 + 30) = 0.5833
    assert v["eff_home"] == pytest.approx(0.5833, abs=0.001)
    assert v["eff_away"] == pytest.approx(0.4167, abs=0.001)
    # hk_home_5  = (0.05 + 0.4167) / 0.5833 = 0.800  ← 下线
    assert v["hk_home_5"] == pytest.approx(0.800, abs=0.005)
    # hk_home_28 = (0.28 + 0.4167) / 0.5833 = 1.194  ← 上线
    assert v["hk_home_28"] == pytest.approx(1.194, abs=0.005)
    # hk_away_5  = (0.05 + 0.5833) / 0.4167 = 1.520
    assert v["hk_away_5"] == pytest.approx(1.520, abs=0.005)
    # hk_away_28 = (0.28 + 0.5833) / 0.4167 = 2.072
    assert v["hk_away_28"] == pytest.approx(2.072, abs=0.005)

    assert v["selection"] == "home"
    # strength = min(2 * |0.5833 - 0.5|, 1.0) = 0.167
    assert result["strength"] == pytest.approx(0.167, abs=0.005)


@pytest.mark.asyncio
async def test_half_ball_home_fav_line_labelled(db, tmp_path):
    """Main FT AH line = -0.5 (home favoured by half ball) → ah_label='half_home'."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 2, 51, ?, 'kickoff', ?, '2026-05-18T10:00:00')""",
            [("home_m05", 1.95), ("away_p05", 1.95)],
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is not None
    v = json.loads(result["value_json"])
    assert v["ah_line"] == pytest.approx(-0.5, abs=1e-6)
    assert v["ah_label"] == "half_home"


@pytest.mark.asyncio
async def test_returns_none_when_ah_out_of_range(db, tmp_path):
    """Main FT AH line outside [-0.5, +0.5] → no signal (script's filter)."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 2, 51, ?, 'kickoff', ?, '2026-05-18T10:00:00')""",
            [("home_m1", 1.90), ("away_p1", 1.90)],
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_ht_pct_missing(db, tmp_path):
    """historical_predictions row exists but HT columns NULL → no signal."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute(
            """UPDATE historical_predictions
               SET home_win_ht_pct=NULL, draw_ht_pct=NULL, away_win_ht_pct=NULL
               WHERE fixture_id=20""",
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_no_ah_rows(db, tmp_path):
    """No AH market_id=51 rows at all → no signal."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is None


@pytest.mark.asyncio
async def test_falls_back_to_pinnacle_when_bet365_missing(db, tmp_path):
    """BET365 (id=2) absent but Pinnacle (id=1) present → still resolves a main line."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 1, 51, ?, 'kickoff', ?, '2026-05-18T10:00:00')""",
            [("home_0", 1.95), ("away_0", 1.85)],
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is not None
    assert json.loads(result["value_json"])["ah_label"] == "draw"


@pytest.mark.asyncio
async def test_main_line_filtered_when_odds_out_of_range(db, tmp_path):
    """Per OA_HT_V2.py:119, lines whose either side is outside [0.6, 2.5]
    are excluded from "main line" candidates. If only such extreme lines
    exist, no signal fires.

    Setup: line 0 with odds 3.20 / 1.30 (home odds too high) — only AH
    line available, all in same waypoint. Should NOT be picked as main.
    """
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 2, 51, ?, 'kickoff', ?, '2026-05-18T10:00:00')""",
            [
                # home side out of [0.6, 2.5] → excluded
                ("home_0", 3.20), ("away_0", 1.30),
                # also try -0.5 line with extreme odds → excluded too
                ("home_m05", 4.50), ("away_p05", 1.15),
            ],
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is None  # nothing qualifies as main line


@pytest.mark.asyncio
async def test_main_line_picks_in_range_over_out_of_range(db, tmp_path):
    """When two lines exist — one in [0.6, 2.5] and one out — the in-range
    one wins, even if the out-of-range one has smaller two-side diff."""
    async with aiosqlite.connect(str(tmp_path / "test.db")) as conn:
        await conn.execute("DELETE FROM historical_odds WHERE fixture_id=20")
        await conn.executemany(
            """INSERT INTO historical_odds
                 (fixture_id, bookmaker_id, market_id, outcome,
                  waypoint, odds, captured_at)
               VALUES (20, 2, 51, ?, 'kickoff', ?, '2026-05-18T10:00:00')""",
            [
                # line 0: in range, larger diff (0.15)
                ("home_0", 2.00), ("away_0", 1.85),
                # line -0.5: out of range (both sides < 0.6), tighter diff (0.05)
                #   but DISQUALIFIED by [0.6, 2.5] gate
                ("home_m05", 0.50), ("away_p05", 0.55),
            ],
        )
        await conn.commit()
    from services.signals.gs_ht_ev import GSHtEv
    result = await GSHtEv().compute(db, fixture_id=20, waypoint="kickoff")
    assert result is not None
    v = json.loads(result["value_json"])
    # Despite line -0.5 having tighter diff, it's filtered out → line 0 wins
    assert v["ah_line"] == pytest.approx(0.0)
    assert v["ah_label"] == "draw"


@pytest.mark.asyncio
async def test_signal_metadata(db):
    from services.signals.gs_ht_ev import GSHtEv
    sig = GSHtEv()
    assert sig.signal_type == "GS-KEN-HT-EV"
    assert sig.signal_version == "v1.0"
    assert sig.scope == "public"
