"""Paper-trading core workers — House Book auto-follow + FT settlement.

Two functions under test:
  place_house_bets(db, book_type, threshold, signal_type='GS-Mispricing')
    → scan signals_snapshot for delta_pct > threshold (positive edge only),
      INSERT OR IGNORE into simulated_bets with user_id=0 sentinel.

  settle_bets(db)
    → for every pending bet (outcome IS NULL), if its fixture is FT and has
      score_home/away, compute pnl_units and copy historical_odds.kickoff as
      closing_odds for CLV.

Both are idempotent: re-running on the same state must produce zero side effects.
"""
from __future__ import annotations

import json

import aiosqlite
import pytest


NOW = "2026-05-18T10:00:00"
KICKOFF_FUTURE = "2026-05-19T15:00:00"  # 29h ahead of NOW


async def _seed_signal_fixture(
    db_path: str,
    fixture_id: int,
    *,
    delta_pct: float,
    selection: str = "home",
    entry_odds: float = 2.10,
    status: str = "NS",
    score_home: int | None = None,
    score_away: int | None = None,
    closing_odds: float | None = None,
):
    """Create one fixture + GS-Mispricing signal + Pinnacle 1X2 historical_odds
    at waypoint='kickoff'. Optionally mark FT with a score."""
    closing = closing_odds if closing_odds is not None else entry_odds
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, score_home, score_away,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, 100, 'L', 'A', 'B', ?, ?, ?, ?, ?, ?)""",
            (fixture_id, score_home, score_away, KICKOFF_FUTURE, status, NOW, NOW),
        )
        await db.execute(
            """INSERT INTO signals_snapshot
                 (fixture_id, signal_type, signal_version, waypoint,
                  scope, value_json, strength, captured_at)
               VALUES (?, 'GS-Mispricing', 'v1.0', 'kickoff', 'public', ?, ?, ?)""",
            (fixture_id,
             json.dumps({"delta_pct": delta_pct, "selection": selection}),
             min(abs(delta_pct) / 10.0, 1.0), NOW),
        )
        for outcome in ("home", "draw", "away"):
            await db.execute(
                """INSERT INTO historical_odds
                     (fixture_id, bookmaker_id, market_id, outcome, waypoint, odds, captured_at)
                   VALUES (?, 1, 6, ?, 'kickoff', ?, ?)""",
                (fixture_id, outcome,
                 closing if outcome == selection else 3.40,
                 NOW),
            )
        await db.commit()


@pytest.fixture
async def db_path(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("GOALCAST_JWT_SECRET", "test-secret-not-prod")
    monkeypatch.setenv("ODDALERTS_API_KEY", "ci-stub")
    import importlib, database
    importlib.reload(database)
    await database.init_db()
    return str(tmp_path / "test.db")


# ---------- place_house_bets ----------

@pytest.mark.asyncio
async def test_place_house_bets_writes_one_row_for_positive_edge(db_path):
    """delta_pct=7.5 > 5.0 threshold and positive → 1 row in simulated_bets."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5,
                                 selection="home", entry_odds=2.10)
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        async with db.execute("SELECT * FROM simulated_bets") as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    assert inserted == 1
    assert len(rows) == 1
    bet = rows[0]
    assert bet["book_type"] == "house_5pct"
    assert bet["user_id"] == 0
    assert bet["fixture_id"] == 10
    assert bet["selection"] == "home"
    assert bet["stake_units"] == 1.0
    assert bet["entry_odds"] == pytest.approx(2.10)
    assert bet["entry_waypoint"] == "kickoff"
    assert bet["signal_type"] == "GS-Mispricing"
    assert bet["signal_version"] == "v1.0"
    assert bet["outcome"] is None
    assert bet["settled_at"] is None


@pytest.mark.asyncio
async def test_place_house_bets_is_idempotent(db_path):
    """Second run on the same data inserts zero (UNIQUE constraint guards it)."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5)
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        first = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        second = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        async with db.execute("SELECT COUNT(*) AS n FROM simulated_bets") as cur:
            n = (await cur.fetchone())["n"]
    assert first == 1
    assert second == 0
    assert n == 1


@pytest.mark.asyncio
async def test_place_house_bets_skips_under_threshold(db_path):
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=3.0)  # below 5
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
    assert inserted == 0


@pytest.mark.asyncio
async def test_place_house_bets_skips_negative_edge(db_path):
    """delta < 0 means market over-estimates that selection — House Book
    follows positive edge only."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=-7.0)
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
    assert inserted == 0


@pytest.mark.asyncio
async def test_place_house_bets_skips_finished_fixtures(db_path):
    """Once a fixture is FT we never place new House Book bets on it."""
    await _seed_signal_fixture(
        db_path, fixture_id=10, delta_pct=7.5,
        status="FT", score_home=2, score_away=0,
    )
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        inserted = await place_house_bets(db, book_type="house_5pct", threshold=5.0)
    assert inserted == 0


# ---------- settle_bets ----------

@pytest.mark.asyncio
async def test_settle_bets_marks_win_and_computes_pnl(db_path):
    """Bet on home, fixture goes FT 2-0 → outcome='win',
    pnl = stake * (entry_odds - 1) = 1.10."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5,
                                 selection="home", entry_odds=2.10)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=2, score_away=0 WHERE id=10"
        )
        await db.commit()
        settled = await settle_bets(db)
        async with db.execute("SELECT * FROM simulated_bets WHERE fixture_id=10") as cur:
            bet = dict(await cur.fetchone())
    assert settled == 1
    assert bet["outcome"] == "win"
    assert bet["pnl_units"] == pytest.approx(1.10, abs=0.001)
    assert bet["settled_at"] is not None
    assert bet["closing_odds"] == pytest.approx(2.10, abs=0.001)


@pytest.mark.asyncio
async def test_settle_bets_marks_loss(db_path):
    """Bet on home, fixture goes FT 0-2 → outcome='loss', pnl=-1."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5,
                                 selection="home", entry_odds=2.10)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=0, score_away=2 WHERE id=10"
        )
        await db.commit()
        await settle_bets(db)
        async with db.execute("SELECT outcome, pnl_units FROM simulated_bets WHERE fixture_id=10") as cur:
            bet = dict(await cur.fetchone())
    assert bet["outcome"] == "loss"
    assert bet["pnl_units"] == pytest.approx(-1.0, abs=0.001)


@pytest.mark.asyncio
async def test_settle_bets_skips_pending_fixtures(db_path):
    """Fixture still NS — settlement leaves the bet pending."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        settled = await settle_bets(db)
        async with db.execute("SELECT outcome FROM simulated_bets WHERE fixture_id=10") as cur:
            row = await cur.fetchone()
    assert settled == 0
    assert row["outcome"] is None


@pytest.mark.asyncio
async def test_settle_bets_does_not_resettle_already_resolved(db_path):
    """An already-settled bet must not be touched on subsequent runs."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=2, score_away=0 WHERE id=10"
        )
        await db.commit()
        first = await settle_bets(db)
        async with db.execute("SELECT settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            first_settled = (await cur.fetchone())["settled_at"]
        second = await settle_bets(db)
        async with db.execute("SELECT settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            second_settled = (await cur.fetchone())["settled_at"]
    assert first == 1
    assert second == 0
    assert first_settled == second_settled


@pytest.mark.asyncio
async def test_three_book_types_run_in_parallel_per_fixture(db_path):
    """Same fixture, same signal: thresholds 3/5/7 all trigger when delta=8 →
    three rows (one per book_type) without UNIQUE conflict."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=8.0)
    from services.paper_trading import place_house_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_3pct", threshold=3.0)
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await place_house_bets(db, book_type="house_7pct", threshold=7.0)
        async with db.execute("SELECT book_type FROM simulated_bets WHERE fixture_id=10") as cur:
            book_types = {r["book_type"] for r in await cur.fetchall()}
    assert book_types == {"house_3pct", "house_5pct", "house_7pct"}


# ---------- house_book_summary ----------

async def _seed_settled_bet(
    db_path: str, *, fixture_id: int, book_type: str,
    selection: str, entry_odds: float, score_home: int, score_away: int,
    settled_at: str,
):
    """Helper: insert a fixture + a simulated_bet already settled."""
    won = (
        (selection == "home" and score_home > score_away)
        or (selection == "draw" and score_home == score_away)
        or (selection == "away" and score_home < score_away)
    )
    pnl = (entry_odds - 1) if won else -1.0
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, score_home, score_away,
               kickoff_utc, status, fetched_at, updated_at)
               VALUES (?, 100, 'L', 'A', 'B', ?, ?, '2026-05-10T15:00:00', 'FT', ?, ?)""",
            (fixture_id, score_home, score_away, NOW, NOW),
        )
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_type, user_id, fixture_id, selection, stake_units,
                  entry_odds, entry_at, entry_waypoint, signal_type, signal_version,
                  outcome, pnl_units, settled_at, closing_odds)
               VALUES (?, 0, ?, ?, 1.0, ?, ?, 'kickoff', 'GS-Mispricing', 'v1.0', ?, ?, ?, ?)""",
            (book_type, fixture_id, selection, entry_odds, NOW,
             "win" if won else "loss", pnl, settled_at, entry_odds),
        )
        await db.commit()


@pytest.mark.asyncio
async def test_house_book_summary_aggregates_settled_bets(db_path):
    """3 settled bets in house_5pct (2 win + 1 loss, total pnl = +2.10) →
    bankroll.current = 1002.10, win_rate = 2/3, roi = 2.10 / 3 stakes = 70%."""
    await _seed_settled_bet(db_path, fixture_id=11, book_type="house_5pct",
                              selection="home", entry_odds=2.10,
                              score_home=2, score_away=0,
                              settled_at="2026-05-12T15:00:00")
    await _seed_settled_bet(db_path, fixture_id=12, book_type="house_5pct",
                              selection="home", entry_odds=1.80,
                              score_home=0, score_away=2,
                              settled_at="2026-05-13T15:00:00")
    await _seed_settled_bet(db_path, fixture_id=13, book_type="house_5pct",
                              selection="away", entry_odds=3.00,
                              score_home=0, score_away=1,
                              settled_at="2026-05-14T15:00:00")
    # One pending bet on the same book.
    await _seed_signal_fixture(db_path, fixture_id=14, delta_pct=7.5)
    from services.paper_trading import place_house_bets, house_book_summary
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        d = await house_book_summary(db, book_type="house_5pct", start_bankroll=1000.0)

    assert d["book_type"] == "house_5pct"
    assert d["bets_settled"] == 3
    assert d["bets_pending"] == 1
    assert d["bankroll"]["start"] == 1000.0
    assert d["bankroll"]["current"] == pytest.approx(1002.10, abs=0.01)
    assert d["metrics"]["win_rate"] == pytest.approx(2 / 3, abs=0.001)
    # ROI = total_pnl / total_stake = 2.10 / 3 = 0.70
    assert d["metrics"]["roi_pct"] == pytest.approx(70.0, abs=0.5)
    # Timeseries ordered by settled_at ASC.
    ts = d["timeseries"]
    assert len(ts) == 3
    assert [p["settled_at"] for p in ts] == [
        "2026-05-12T15:00:00", "2026-05-13T15:00:00", "2026-05-14T15:00:00",
    ]
    assert ts[0]["bankroll"] == pytest.approx(1001.10, abs=0.01)
    assert ts[1]["bankroll"] == pytest.approx(1000.10, abs=0.01)
    assert ts[2]["bankroll"] == pytest.approx(1002.10, abs=0.01)


@pytest.mark.asyncio
async def test_house_book_summary_filters_by_book_type(db_path):
    """Mixed bets across book_types — summary returns only the requested band."""
    await _seed_settled_bet(db_path, fixture_id=11, book_type="house_5pct",
                              selection="home", entry_odds=2.10,
                              score_home=2, score_away=0,
                              settled_at="2026-05-12T15:00:00")
    await _seed_settled_bet(db_path, fixture_id=12, book_type="house_3pct",
                              selection="home", entry_odds=2.10,
                              score_home=2, score_away=0,
                              settled_at="2026-05-12T15:00:00")
    from services.paper_trading import house_book_summary
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        d5 = await house_book_summary(db, book_type="house_5pct", start_bankroll=1000.0)
        d3 = await house_book_summary(db, book_type="house_3pct", start_bankroll=1000.0)
    assert d5["bets_settled"] == 1
    assert d3["bets_settled"] == 1


@pytest.mark.asyncio
async def test_house_book_summary_empty_state(db_path):
    """No bets at all → bankroll unchanged, roi=null, timeseries empty."""
    from services.paper_trading import house_book_summary
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        d = await house_book_summary(db, book_type="house_5pct", start_bankroll=1000.0)
    assert d["bets_settled"] == 0
    assert d["bets_pending"] == 0
    assert d["bets_voided"] == 0
    assert d["bankroll"]["current"] == 1000.0
    assert d["metrics"]["roi_pct"] is None
    assert d["metrics"]["win_rate"] is None
    assert d["timeseries"] == []


# ---------- settle_bets corner cases (day-6 健壮性) ----------

@pytest.mark.asyncio
async def test_settle_bets_rescoring_after_correction(db_path):
    """Bet on home, fixture goes FT 2-0 → 'win'. Then score corrected to 0-2
    (e.g., post-match administrative ruling). Next settle pass must downgrade
    to 'loss' with pnl=-1, and bump settled_at — silent stale data violates
    'audit-style ledger' promise."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5,
                                 selection="home", entry_odds=2.10)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=2, score_away=0 WHERE id=10"
        )
        await db.commit()
        await settle_bets(db)
        async with db.execute("SELECT outcome, pnl_units, settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            first = dict(await cur.fetchone())
        # Administrative correction: actual was 0-2.
        await db.execute(
            "UPDATE fixtures SET score_home=0, score_away=2 WHERE id=10"
        )
        await db.commit()
        # Tiny sleep so settled_at strictly advances (timestamps have second resolution).
        import asyncio
        await asyncio.sleep(0.01)
        changed = await settle_bets(db)
        async with db.execute("SELECT outcome, pnl_units, settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            second = dict(await cur.fetchone())
    assert first["outcome"] == "win"
    assert changed == 1
    assert second["outcome"] == "loss"
    assert second["pnl_units"] == pytest.approx(-1.0, abs=0.001)
    assert second["settled_at"] >= first["settled_at"]


@pytest.mark.asyncio
async def test_settle_bets_resets_to_pending_when_fixture_reverts_to_ns(db_path):
    """Settled bet; then fixture is reverted to NS (e.g., match postponed and
    upstream feed un-finalizes it). Bet must drop back to pending — leaving
    a 'win'/'loss' marker on a future match would poison ROI."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5,
                                 selection="home", entry_odds=2.10)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=2, score_away=0 WHERE id=10"
        )
        await db.commit()
        await settle_bets(db)
        # Upstream reverts.
        await db.execute(
            "UPDATE fixtures SET status='NS', score_home=NULL, score_away=NULL WHERE id=10"
        )
        await db.commit()
        changed = await settle_bets(db)
        async with db.execute(
            "SELECT outcome, pnl_units, settled_at FROM simulated_bets WHERE fixture_id=10"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert changed == 1
    assert bet["outcome"] is None
    assert bet["pnl_units"] is None
    assert bet["settled_at"] is None


@pytest.mark.asyncio
async def test_settle_bets_voids_cancelled_or_postponed(db_path):
    """fixture.status='PST' (postponed) or 'CAN'/'ABD'/'AWD'/'WO' → outcome='void'
    with pnl=0. Real bookmakers refund stake; the virtual ledger mirrors that
    by reporting zero PnL, and excludes void bets from ROI/win_rate denominators."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute("UPDATE fixtures SET status='PST' WHERE id=10")
        await db.commit()
        changed = await settle_bets(db)
        async with db.execute(
            "SELECT outcome, pnl_units FROM simulated_bets WHERE fixture_id=10"
        ) as cur:
            bet = dict(await cur.fetchone())
    assert changed == 1
    assert bet["outcome"] == "void"
    assert bet["pnl_units"] == pytest.approx(0.0, abs=0.001)


@pytest.mark.asyncio
async def test_settle_bets_no_change_path_is_truly_idempotent(db_path):
    """Bet settled cleanly, fixture untouched → subsequent settle calls report
    `changed=0` AND leave settled_at exactly as-is (no silent UPDATE churn)."""
    await _seed_signal_fixture(db_path, fixture_id=10, delta_pct=7.5)
    from services.paper_trading import place_house_bets, settle_bets
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        await place_house_bets(db, book_type="house_5pct", threshold=5.0)
        await db.execute(
            "UPDATE fixtures SET status='FT', score_home=2, score_away=0 WHERE id=10"
        )
        await db.commit()
        first_changed = await settle_bets(db)
        async with db.execute("SELECT settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            t1 = (await cur.fetchone())["settled_at"]
        second_changed = await settle_bets(db)
        async with db.execute("SELECT settled_at FROM simulated_bets WHERE fixture_id=10") as cur:
            t2 = (await cur.fetchone())["settled_at"]
    assert first_changed == 1
    assert second_changed == 0
    assert t1 == t2


@pytest.mark.asyncio
async def test_house_book_summary_excludes_void_from_roi(db_path):
    """Two settled bets (win + loss) and one void → ROI/win_rate computed
    only over the 2 graded bets; bets_voided surfaced separately; void's
    pnl=0 does not skew bankroll."""
    await _seed_settled_bet(db_path, fixture_id=11, book_type="house_5pct",
                              selection="home", entry_odds=2.0,
                              score_home=2, score_away=0,  # win, pnl=+1.0
                              settled_at="2026-05-12T15:00:00")
    await _seed_settled_bet(db_path, fixture_id=12, book_type="house_5pct",
                              selection="home", entry_odds=2.0,
                              score_home=0, score_away=2,  # loss, pnl=-1.0
                              settled_at="2026-05-13T15:00:00")
    # Manually inject a voided row (no score; status irrelevant for summary).
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """INSERT INTO fixtures (id, competition_id, competition_name,
               home_team, away_team, kickoff_utc, status, fetched_at, updated_at)
               VALUES (13, 100, 'L', 'A', 'B', '2026-05-14T15:00:00', 'PST', ?, ?)""",
            (NOW, NOW),
        )
        await db.execute(
            """INSERT INTO simulated_bets
                 (book_type, user_id, fixture_id, selection, stake_units,
                  entry_odds, entry_at, entry_waypoint, signal_type, signal_version,
                  outcome, pnl_units, settled_at)
               VALUES ('house_5pct', 0, 13, 'home', 1.0, 2.0, ?, 'kickoff',
                       'GS-Mispricing', 'v1.0', 'void', 0.0, '2026-05-14T15:00:00')""",
            (NOW,),
        )
        await db.commit()
    from services.paper_trading import house_book_summary
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        d = await house_book_summary(db, book_type="house_5pct", start_bankroll=1000.0)
    assert d["bets_settled"] == 3   # win + loss + void
    assert d["bets_voided"] == 1
    # ROI denominator excludes void: total_pnl=0, total_stake=2 → 0%
    assert d["metrics"]["roi_pct"] == pytest.approx(0.0, abs=0.5)
    # win_rate denominator excludes void: 1 win / 2 graded = 0.5
    assert d["metrics"]["win_rate"] == pytest.approx(0.5, abs=0.001)
    # Bankroll: +1 - 1 + 0 = 1000 unchanged.
    assert d["bankroll"]["current"] == pytest.approx(1000.0, abs=0.01)
