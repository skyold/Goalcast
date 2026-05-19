import os
import aiosqlite

def _db_path() -> str:
    # Default aligned with docker-compose.yml + .github/workflows/ci.yml +
    # config.py::Settings.goalcast_db_path so local CLI scripts (seed,
    # backfill) write into the same SQLite file the running backend reads,
    # not a phantom backend/goalcast.db sibling.
    return os.getenv("GOALCAST_DB_PATH", "data/goalcast.db")

CREATE_FIXTURES = """
CREATE TABLE IF NOT EXISTS fixtures (
    id              INTEGER PRIMARY KEY,
    competition_id  INTEGER NOT NULL,
    competition_name TEXT NOT NULL,
    home_team       TEXT NOT NULL,
    away_team       TEXT NOT NULL,
    home_team_id    INTEGER,
    away_team_id    INTEGER,
    kickoff_utc     DATETIME NOT NULL,
    status          TEXT DEFAULT 'pre',
    score_home      INTEGER,
    score_away      INTEGER,
    prob_home_win   REAL,
    prob_draw       REAL,
    prob_away_win   REAL,
    trend_home_win  INTEGER DEFAULT 0,
    trend_away_win  INTEGER DEFAULT 0,
    trend_btts      INTEGER DEFAULT 0,
    home_stats      TEXT,
    away_stats      TEXT,
    h2h             TEXT,
    fetched_at      DATETIME NOT NULL,
    updated_at      DATETIME NOT NULL
)
"""
CREATE_FIXTURES_IDX1 = "CREATE INDEX IF NOT EXISTS idx_fixtures_date_comp ON fixtures(date(kickoff_utc), competition_id)"
CREATE_FIXTURES_IDX2 = "CREATE INDEX IF NOT EXISTS idx_fixtures_status ON fixtures(status)"
CREATE_ODDS = """
CREATE TABLE IF NOT EXISTS odds_snapshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    fixture_id  INTEGER NOT NULL REFERENCES fixtures(id),
    market      TEXT NOT NULL,
    bookmaker   TEXT NOT NULL,
    odds_home   REAL,
    odds_draw   REAL,
    odds_away   REAL,
    drop_pct    REAL,
    drop_market TEXT,
    recorded_at DATETIME NOT NULL
)
"""
CREATE_ODDS_IDX1 = "CREATE INDEX IF NOT EXISTS idx_odds_fixture ON odds_snapshots(fixture_id, recorded_at)"
CREATE_ODDS_IDX2 = "CREATE INDEX IF NOT EXISTS idx_odds_drop ON odds_snapshots(drop_pct, recorded_at)"
CREATE_SYNC_LOG = """
CREATE TABLE IF NOT EXISTS sync_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type   TEXT NOT NULL,
    status      TEXT NOT NULL,
    records     INTEGER DEFAULT 0,
    error_msg   TEXT,
    started_at  DATETIME NOT NULL,
    finished_at DATETIME
)
"""

CREATE_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS predictions (
    fixture_id   INTEGER PRIMARY KEY REFERENCES fixtures(id),
    simulations  INTEGER NOT NULL DEFAULT 0,
    home_win     INTEGER, draw INTEGER, away_win INTEGER,
    btts         INTEGER,
    o15_goals    INTEGER, o25_goals INTEGER, o35_goals INTEGER, o45_goals INTEGER,
    scorelines   TEXT,
    updated_at   DATETIME NOT NULL
)
"""

CREATE_TEAM_FORM = """
CREATE TABLE IF NOT EXISTS team_form (
    team_id        INTEGER NOT NULL,
    season_id      INTEGER NOT NULL,
    form5_str      TEXT NOT NULL DEFAULT '',
    played         INTEGER, won INTEGER, drawn INTEGER, lost INTEGER,
    goals_for      INTEGER, goals_against INTEGER, goals_avg REAL,
    updated_at     DATETIME NOT NULL,
    PRIMARY KEY (team_id, season_id)
)
"""

CREATE_BOOKMAKER_ODDS = """
CREATE TABLE IF NOT EXISTS bookmaker_odds (
    fixture_id    INTEGER NOT NULL REFERENCES fixtures(id),
    bookmaker_id  INTEGER NOT NULL,
    market_id     INTEGER NOT NULL,
    outcome       TEXT NOT NULL,
    opening       REAL,
    current       REAL,
    peak          REAL,
    opening_at    DATETIME,
    current_at    DATETIME,
    PRIMARY KEY (fixture_id, bookmaker_id, market_id, outcome)
)
"""
CREATE_BO_IDX1 = "CREATE INDEX IF NOT EXISTS idx_bo_fix ON bookmaker_odds(fixture_id)"
CREATE_BO_IDX2 = "CREATE INDEX IF NOT EXISTS idx_bo_fix_market ON bookmaker_odds(fixture_id, market_id)"

CREATE_COMPETITIONS = """
CREATE TABLE IF NOT EXISTS competitions (
    id              INTEGER PRIMARY KEY,
    name_en         TEXT NOT NULL,
    name_zh         TEXT,
    country         TEXT,
    last_synced_at  DATETIME
)
"""

CREATE_TEAMS = """
CREATE TABLE IF NOT EXISTS teams (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    name_zh         TEXT,
    short_code      TEXT,
    country         TEXT,
    last_synced_at  DATETIME
)
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_USER_SETTINGS = """
CREATE TABLE IF NOT EXISTS user_settings (
    user_id  INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    locale   TEXT NOT NULL DEFAULT 'zh'
)
"""

CREATE_USER_COMPETITION_PREFS = """
CREATE TABLE IF NOT EXISTS user_competition_prefs (
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    competition_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, competition_id)
)
"""

CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fixture_id   INTEGER NOT NULL,
    alert_type   TEXT    NOT NULL,
    payload      TEXT    NOT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dismissed_at TIMESTAMP,
    expires_at   TIMESTAMP NOT NULL
)
"""
CREATE_ALERTS_IDX = "CREATE INDEX IF NOT EXISTS idx_alerts_user_active ON alerts(user_id, dismissed_at, expires_at)"

CREATE_USER_ALERT_SETTINGS = """
CREATE TABLE IF NOT EXISTS user_alert_settings (
    user_id              INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    divergence_threshold REAL    NOT NULL DEFAULT 5.0,
    enabled              INTEGER NOT NULL DEFAULT 1
)
"""

# Snapshot pipeline tables. predictions and bookmaker_odds tables upsert
# (rows overwritten as kickoff approaches) so pre-game state is lost the moment
# a fixture transitions to FT. These two history tables capture predictions
# and odds at five waypoints (T-48h / T-24h / T-6h / T-1h / kickoff) so that
# backward-looking metrics (model hit rate / CLV / upset rate) remain computable.
CREATE_HISTORICAL_PREDICTIONS = """
CREATE TABLE IF NOT EXISTS historical_predictions (
    fixture_id    INTEGER NOT NULL,
    waypoint      TEXT    NOT NULL,
    simulations   INTEGER NOT NULL,
    home_win_pct  REAL    NOT NULL,
    draw_pct      REAL    NOT NULL,
    away_win_pct  REAL    NOT NULL,
    btts_pct      REAL,
    o25_pct       REAL,
    scorelines    TEXT,
    captured_at   TIMESTAMP NOT NULL,
    PRIMARY KEY (fixture_id, waypoint)
)
"""
CREATE_HISTORICAL_PREDICTIONS_IDX = "CREATE INDEX IF NOT EXISTS idx_hist_pred_waypoint ON historical_predictions(waypoint)"

CREATE_HISTORICAL_ODDS = """
CREATE TABLE IF NOT EXISTS historical_odds (
    fixture_id    INTEGER NOT NULL,
    bookmaker_id  INTEGER NOT NULL,
    market_id     INTEGER NOT NULL,
    outcome       TEXT    NOT NULL,
    waypoint      TEXT    NOT NULL,
    odds          REAL    NOT NULL,
    captured_at   TIMESTAMP NOT NULL,
    PRIMARY KEY (fixture_id, bookmaker_id, market_id, outcome, waypoint)
)
"""
CREATE_HISTORICAL_ODDS_IDX = "CREATE INDEX IF NOT EXISTS idx_hist_odds_fix ON historical_odds(fixture_id, waypoint)"

# Catalog methodology text per signal × locale. Consumed by
# /api/signals/catalog. Decoupling文案 from code so that markdown bodies can be
# updated without redeploying (seed via scripts/seed_methodology.py). See
# docs/PRD/signal-catalog-and-subscriptions.prd.md Q1 — chose DB over static
# constants to match the competitions.name_zh "DB-as-translation" pattern.
CREATE_SIGNAL_METHODOLOGY = """
CREATE TABLE IF NOT EXISTS signal_methodology (
    signal_type  TEXT NOT NULL,
    locale       TEXT NOT NULL,
    body_md      TEXT NOT NULL,
    updated_at   TIMESTAMP NOT NULL,
    PRIMARY KEY (signal_type, locale)
)
"""

# Goalcast Signals snapshot. One row per (fixture, signal_type, waypoint).
# Written by services.signals via snapshot.py after historical_* rows for
# the same (fixture, waypoint) land. See docs/PRD/proprietary-signals.prd.md.
CREATE_SIGNALS_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS signals_snapshot (
    fixture_id     INTEGER NOT NULL,
    signal_type    TEXT    NOT NULL,
    signal_version TEXT    NOT NULL,
    waypoint       TEXT    NOT NULL,
    scope          TEXT    NOT NULL,
    value_json     TEXT    NOT NULL,
    strength       REAL,
    captured_at    TIMESTAMP NOT NULL,
    PRIMARY KEY (fixture_id, signal_type, waypoint)
)
"""
CREATE_SIGNALS_SNAPSHOT_IDX_RANK = "CREATE INDEX IF NOT EXISTS idx_ss_type_strength ON signals_snapshot(signal_type, strength DESC)"
CREATE_SIGNALS_SNAPSHOT_IDX_FIX  = "CREATE INDEX IF NOT EXISTS idx_ss_fixture       ON signals_snapshot(fixture_id)"

# Per-signal Book catalogue. Phase 4 of signal-catalog-and-subscriptions PRD —
# "信号即账户": each REGISTERED signal gets a row with user_id=0 ("House Book"),
# users can fork to their own user_id>0 row. One book ↔ one signal binding;
# conditions_json filters which signal_snapshot rows that book trades on.
#
# Backward compat: simulated_bets keeps `book_type TEXT` column (legacy unique
# constraint still in force). New writes set both book_type AND book_id; legacy
# rows are backfilled on init.
CREATE_SIMULATED_BOOKS = """
CREATE TABLE IF NOT EXISTS simulated_books (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    name            TEXT    NOT NULL,
    signal_type     TEXT    NOT NULL,
    signal_version  TEXT    NOT NULL,
    conditions_json TEXT    NOT NULL DEFAULT '{}',
    starting_units  REAL    NOT NULL DEFAULT 100.0,
    match_scope     TEXT    NOT NULL DEFAULT 'all',
    created_at      TIMESTAMP NOT NULL,
    archived_at     TIMESTAMP,
    UNIQUE (user_id, name)
)
"""
CREATE_SB_BOOKS_IDX_USER   = "CREATE INDEX IF NOT EXISTS idx_sb_books_user   ON simulated_books(user_id, archived_at)"
CREATE_SB_BOOKS_IDX_SIGNAL = "CREATE INDEX IF NOT EXISTS idx_sb_books_signal ON simulated_books(signal_type, signal_version)"

# Paper-trading virtual ledger. House Book (user_id=0 sentinel) auto-follows
# Goalcast signals; Personal Book (user_id>0, future) records manual entries.
# See docs/PRD/paper-trading.prd.md. user_id is NOT NULL with sentinel 0 because
# SQLite UNIQUE treats NULL as distinct — using NULL for House Book would let
# duplicates slip past the unique constraint.
CREATE_SIMULATED_BETS = """
CREATE TABLE IF NOT EXISTS simulated_bets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    book_type       TEXT    NOT NULL,
    user_id         INTEGER NOT NULL DEFAULT 0,
    fixture_id      INTEGER NOT NULL,
    selection       TEXT    NOT NULL,
    stake_units     REAL    NOT NULL,
    entry_odds      REAL    NOT NULL,
    entry_at        TIMESTAMP NOT NULL,
    entry_waypoint  TEXT    NOT NULL,
    signal_type     TEXT,
    signal_version  TEXT,
    outcome         TEXT,
    pnl_units       REAL,
    settled_at      TIMESTAMP,
    closing_odds    REAL,
    UNIQUE (book_type, fixture_id, selection, user_id)
)
"""
CREATE_SB_IDX_BOOK_SETTLED    = "CREATE INDEX IF NOT EXISTS idx_sb_book_settled    ON simulated_bets(book_type, settled_at)"
CREATE_SB_IDX_USER_SETTLED    = "CREATE INDEX IF NOT EXISTS idx_sb_user_settled    ON simulated_bets(user_id, settled_at)"
CREATE_SB_IDX_FIXTURE_PENDING = "CREATE INDEX IF NOT EXISTS idx_sb_fixture_pending ON simulated_bets(fixture_id) WHERE outcome IS NULL"

# Speeds up local form5 derivation (scan fixtures by team_id, status='FT', ORDER BY kickoff DESC).
CREATE_FIXTURES_IDX_HTEAM = "CREATE INDEX IF NOT EXISTS idx_fixtures_home_team ON fixtures(home_team_id, kickoff_utc)"
CREATE_FIXTURES_IDX_ATEAM = "CREATE INDEX IF NOT EXISTS idx_fixtures_away_team ON fixtures(away_team_id, kickoff_utc)"

ALTER_FIXTURES_PRED     = "ALTER TABLE fixtures ADD COLUMN predictability TEXT"
ALTER_FIXTURES_SEASON   = "ALTER TABLE fixtures ADD COLUMN season_id INTEGER"
ALTER_FIXTURES_HOME_POS = "ALTER TABLE fixtures ADD COLUMN home_position INTEGER"
ALTER_FIXTURES_AWAY_POS = "ALTER TABLE fixtures ADD COLUMN away_position INTEGER"
ALTER_FIXTURES_WINNING  = "ALTER TABLE fixtures ADD COLUMN winning_team INTEGER"

# HT 1X2 percentages on historical_predictions (consumed by signals/gs_ht_ev).
# Nullable so legacy rows captured before HT plumbing remain valid; the signal
# returns None when any HT pct is NULL.
ALTER_HIST_PRED_HT_HOME = "ALTER TABLE historical_predictions ADD COLUMN home_win_ht_pct REAL"
ALTER_HIST_PRED_HT_DRAW = "ALTER TABLE historical_predictions ADD COLUMN draw_ht_pct     REAL"
ALTER_HIST_PRED_HT_AWAY = "ALTER TABLE historical_predictions ADD COLUMN away_win_ht_pct REAL"

# Same HT percentages on the live `predictions` upsert table. Written by
# sync_fixtures_upcoming from OA's fixture.probability include; copied into
# historical_predictions by snapshot.py:_capture at each waypoint.
ALTER_PRED_HT_HOME = "ALTER TABLE predictions ADD COLUMN home_win_ht_pct REAL"
ALTER_PRED_HT_DRAW = "ALTER TABLE predictions ADD COLUMN draw_ht_pct     REAL"
ALTER_PRED_HT_AWAY = "ALTER TABLE predictions ADD COLUMN away_win_ht_pct REAL"

# Phase 4 — simulated_bets gains book_id (FK to simulated_books) alongside the
# legacy book_type column. UNIQUE on (book_id, fixture_id, selection) lives in
# a partial index below so legacy rows (book_id IS NULL) don't violate it.
ALTER_SB_BOOK_ID = "ALTER TABLE simulated_bets ADD COLUMN book_id INTEGER"
CREATE_SB_IDX_BOOK_FIXSEL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sb_book_fixsel "
    "ON simulated_bets(book_id, fixture_id, selection) WHERE book_id IS NOT NULL"
)

# Phase B (paper-trading-realism) — simulated_bets gains market_id (which
# market the bet is on) and ah_line (signed AH handicap from the bet's side
# perspective; NULL for 1X2). Settlement dispatches on market_id.
# UNIQUE upgrade includes market_id so a single book could theoretically hold
# bets on different markets for the same fixture without false dedupe.
ALTER_SB_MARKET_ID = "ALTER TABLE simulated_bets ADD COLUMN market_id INTEGER"
ALTER_SB_AH_LINE   = "ALTER TABLE simulated_bets ADD COLUMN ah_line REAL"
CREATE_SB_IDX_BOOK_MARKET_FIXSEL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sb_book_market_fixsel "
    "ON simulated_bets(book_id, fixture_id, market_id, selection) WHERE book_id IS NOT NULL"
)

async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        # WAL mode allows concurrent readers + one writer without disk-image
        # corruption that can occur with the default rollback journal under
        # interrupted long writes. Persistent once set; safe to re-issue.
        await db.execute("PRAGMA journal_mode=WAL")
        for ddl in (
            CREATE_FIXTURES, CREATE_FIXTURES_IDX1, CREATE_FIXTURES_IDX2,
            CREATE_ODDS, CREATE_ODDS_IDX1, CREATE_ODDS_IDX2,
            CREATE_SYNC_LOG,
            CREATE_PREDICTIONS,
            CREATE_TEAM_FORM,
            CREATE_BOOKMAKER_ODDS, CREATE_BO_IDX1, CREATE_BO_IDX2,
            CREATE_COMPETITIONS,
            CREATE_TEAMS,
            CREATE_USERS,
            CREATE_USER_SETTINGS,
            CREATE_USER_COMPETITION_PREFS,
            CREATE_ALERTS,
            CREATE_ALERTS_IDX,
            CREATE_USER_ALERT_SETTINGS,
            CREATE_HISTORICAL_PREDICTIONS,
            CREATE_HISTORICAL_PREDICTIONS_IDX,
            CREATE_HISTORICAL_ODDS,
            CREATE_HISTORICAL_ODDS_IDX,
            CREATE_SIGNAL_METHODOLOGY,
            CREATE_SIGNALS_SNAPSHOT,
            CREATE_SIGNALS_SNAPSHOT_IDX_RANK,
            CREATE_SIGNALS_SNAPSHOT_IDX_FIX,
            CREATE_SIMULATED_BOOKS,
            CREATE_SB_BOOKS_IDX_USER,
            CREATE_SB_BOOKS_IDX_SIGNAL,
            CREATE_SIMULATED_BETS,
            CREATE_SB_IDX_BOOK_SETTLED,
            CREATE_SB_IDX_USER_SETTLED,
            CREATE_SB_IDX_FIXTURE_PENDING,
        ):
            await db.execute(ddl)
        cur = await db.execute("PRAGMA table_info(fixtures)")
        existing = {row[1] for row in await cur.fetchall()}
        if "predictability" not in existing:
            await db.execute(ALTER_FIXTURES_PRED)
        if "season_id" not in existing:
            await db.execute(ALTER_FIXTURES_SEASON)
        if "home_position" not in existing:
            await db.execute(ALTER_FIXTURES_HOME_POS)
        if "away_position" not in existing:
            await db.execute(ALTER_FIXTURES_AWAY_POS)
        if "winning_team" not in existing:
            await db.execute(ALTER_FIXTURES_WINNING)
        # HT 1X2 columns on historical_predictions (idempotent).
        cur = await db.execute("PRAGMA table_info(historical_predictions)")
        hp_existing = {row[1] for row in await cur.fetchall()}
        if "home_win_ht_pct" not in hp_existing:
            await db.execute(ALTER_HIST_PRED_HT_HOME)
        if "draw_ht_pct" not in hp_existing:
            await db.execute(ALTER_HIST_PRED_HT_DRAW)
        if "away_win_ht_pct" not in hp_existing:
            await db.execute(ALTER_HIST_PRED_HT_AWAY)
        # book_id column on simulated_bets (Phase 4 — links bets to simulated_books).
        cur = await db.execute("PRAGMA table_info(simulated_bets)")
        sb_existing = {row[1] for row in await cur.fetchall()}
        if "book_id" not in sb_existing:
            await db.execute(ALTER_SB_BOOK_ID)
        # Partial UNIQUE index — only enforces where book_id IS NOT NULL,
        # so legacy book_type-only rows don't trip it.
        await db.execute(CREATE_SB_IDX_BOOK_FIXSEL)
        # Phase B — market_id + ah_line on simulated_bets. Legacy 1X2 rows
        # (all rows before this migration) get backfilled to market_id=6.
        if "market_id" not in sb_existing:
            await db.execute(ALTER_SB_MARKET_ID)
            await db.execute("UPDATE simulated_bets SET market_id = 6 WHERE market_id IS NULL")
        if "ah_line" not in sb_existing:
            await db.execute(ALTER_SB_AH_LINE)
        await db.execute(CREATE_SB_IDX_BOOK_MARKET_FIXSEL)
        # Same HT columns on the live predictions upsert table (idempotent).
        cur = await db.execute("PRAGMA table_info(predictions)")
        p_existing = {row[1] for row in await cur.fetchall()}
        if "home_win_ht_pct" not in p_existing:
            await db.execute(ALTER_PRED_HT_HOME)
        if "draw_ht_pct" not in p_existing:
            await db.execute(ALTER_PRED_HT_DRAW)
        if "away_win_ht_pct" not in p_existing:
            await db.execute(ALTER_PRED_HT_AWAY)
        # Indexes that reference fixtures.home_team_id / away_team_id must be created
        # AFTER ALTERs (in case those columns were added by an older migration path).
        for ddl in (CREATE_FIXTURES_IDX_HTEAM, CREATE_FIXTURES_IDX_ATEAM):
            await db.execute(ddl)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db
