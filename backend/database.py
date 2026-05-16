import os
import aiosqlite

def _db_path() -> str:
    return os.getenv("GOALCAST_DB_PATH", "goalcast.db")

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

ALTER_FIXTURES_PRED = "ALTER TABLE fixtures ADD COLUMN predictability TEXT"
ALTER_FIXTURES_SEASON = "ALTER TABLE fixtures ADD COLUMN season_id INTEGER"

async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        for ddl in (
            CREATE_FIXTURES, CREATE_FIXTURES_IDX1, CREATE_FIXTURES_IDX2,
            CREATE_ODDS, CREATE_ODDS_IDX1, CREATE_ODDS_IDX2,
            CREATE_SYNC_LOG,
            CREATE_PREDICTIONS,
            CREATE_TEAM_FORM,
            CREATE_BOOKMAKER_ODDS, CREATE_BO_IDX1, CREATE_BO_IDX2,
        ):
            await db.execute(ddl)
        cur = await db.execute("PRAGMA table_info(fixtures)")
        existing = {row[1] for row in await cur.fetchall()}
        if "predictability" not in existing:
            await db.execute(ALTER_FIXTURES_PRED)
        if "season_id" not in existing:
            await db.execute(ALTER_FIXTURES_SEASON)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db
