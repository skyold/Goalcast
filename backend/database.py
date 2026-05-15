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

async def init_db() -> None:
    async with aiosqlite.connect(_db_path()) as db:
        for ddl in (CREATE_FIXTURES, CREATE_FIXTURES_IDX1, CREATE_FIXTURES_IDX2,
                    CREATE_ODDS, CREATE_ODDS_IDX1, CREATE_ODDS_IDX2, CREATE_SYNC_LOG):
            await db.execute(ddl)
        await db.commit()

async def get_db():
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        yield db
