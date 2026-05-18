"""Export all team + competition name mappings (English ↔ 中文).

Writes two artifacts under docs/data/:
    team_names_zh_en.csv   — flat CSV, opens cleanly in Excel
    team_names_zh_en.json  — structured JSON, easy for downstream tooling

Usage:
    cd backend && .venv/bin/python -m scripts.export_team_names
"""
from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path

import aiosqlite

from database import _db_path


OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "data"


async def main() -> None:
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row

        # Teams: column is `name` (English) + `name_zh`.
        async with db.execute(
            "SELECT id, name AS name_en, name_zh, short_code, country "
            "FROM teams ORDER BY country, name"
        ) as cur:
            teams = [dict(r) for r in await cur.fetchall()]

        async with db.execute(
            "SELECT id, name_en, name_zh, country "
            "FROM competitions ORDER BY country, name_en"
        ) as cur:
            comps = [dict(r) for r in await cur.fetchall()]

    csv_path = out_dir / "team_names_zh_en.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "id", "name_en", "name_zh", "short_code", "country"])
        for t in teams:
            w.writerow([
                "team", t["id"], t["name_en"], t["name_zh"] or "",
                t["short_code"] or "", t["country"] or "",
            ])
        for c in comps:
            w.writerow([
                "competition", c["id"], c["name_en"], c["name_zh"] or "",
                "", c["country"] or "",
            ])

    json_path = out_dir / "team_names_zh_en.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "teams": [
                    {
                        "id": t["id"],
                        "name_en": t["name_en"],
                        "name_zh": t["name_zh"],
                        "short_code": t["short_code"],
                        "country": t["country"],
                    } for t in teams
                ],
                "competitions": [
                    {
                        "id": c["id"],
                        "name_en": c["name_en"],
                        "name_zh": c["name_zh"],
                        "country": c["country"],
                    } for c in comps
                ],
            },
            f, ensure_ascii=False, indent=2,
        )

    print(f"exported {len(teams)} teams + {len(comps)} competitions")
    print(f"  CSV  → {csv_path}")
    print(f"  JSON → {json_path}")


if __name__ == "__main__":
    asyncio.run(main())
