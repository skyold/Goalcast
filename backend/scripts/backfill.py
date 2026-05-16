"""One-shot backfill on first deployment: runs jobs in dependency order
so prepopulated tables exist when later jobs read them.

Usage:
    cd backend && .venv/bin/python -m scripts.backfill
"""
import asyncio
from database import init_db
from services.sync import (
    sync_fixtures_upcoming, sync_team_form, sync_ah_odds_seed, sync_predictions,
)

async def main() -> None:
    await init_db()
    print("[1/4] fixtures_upcoming…")
    await sync_fixtures_upcoming()
    print("[2/4] team_form…")
    await sync_team_form()
    print("[3/4] ah_odds_seed…")
    await sync_ah_odds_seed()
    print("[4/4] predictions…")
    await sync_predictions()
    print("done.")

if __name__ == "__main__":
    asyncio.run(main())
