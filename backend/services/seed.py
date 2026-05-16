"""Load static Chinese-name seed files into competitions/teams tables.

Idempotent: re-running is safe. UPSERT preserves an already-populated name_zh
so manual edits in the DB are not clobbered on next startup.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
import aiosqlite

from database import _db_path

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def load_seeds() -> dict:
    comps_path = SEED_DIR / "competitions_zh.json"
    teams_path = SEED_DIR / "teams_zh.json"
    comps = json.loads(comps_path.read_text(encoding="utf-8")) if comps_path.exists() else []
    teams = json.loads(teams_path.read_text(encoding="utf-8")) if teams_path.exists() else []
    now = _now()
    async with aiosqlite.connect(_db_path()) as db:
        for c in comps:
            await db.execute(
                """INSERT INTO competitions (id, name_en, name_zh, country, last_synced_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name_en = excluded.name_en,
                     name_zh = COALESCE(competitions.name_zh, excluded.name_zh),
                     country = COALESCE(excluded.country, competitions.country),
                     last_synced_at = excluded.last_synced_at""",
                (c["id"], c["name_en"], c.get("name_zh"), c.get("country"), now),
            )
        for t in teams:
            await db.execute(
                """INSERT INTO teams (id, name, name_zh, short_code, country, last_synced_at)
                   VALUES(?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name = excluded.name,
                     name_zh = COALESCE(teams.name_zh, excluded.name_zh),
                     country = COALESCE(excluded.country, teams.country),
                     last_synced_at = excluded.last_synced_at""",
                (t["id"], t["name_en"], t.get("name_zh"), t.get("short_code"),
                 t.get("country"), now),
            )
        await db.commit()
    return {"competitions": len(comps), "teams": len(teams)}
