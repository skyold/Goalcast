"""One-shot backfill on first deployment: runs jobs in dependency order
so prepopulated tables exist when later jobs read them.

Usage:
    cd backend && .venv/bin/python -m scripts.backfill
"""
import asyncio
from database import init_db
from services.sync import (
    sync_fixtures_upcoming, sync_team_form, sync_ah_odds_seed,
)

async def main() -> None:
    await init_db()
    print("[1/3] fixtures_upcoming…")
    await sync_fixtures_upcoming()
    print("[2/3] team_form…")
    await sync_team_form()
    print("[3/3] ah_odds_seed…")
    await sync_ah_odds_seed()
    print("done.")

if __name__ == "__main__":
    asyncio.run(main())
