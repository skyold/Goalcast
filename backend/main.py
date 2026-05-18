from contextlib import asynccontextmanager
import aiosqlite
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import _db_path, init_db
from routers import auth, me, fixtures, odds, history, insights, backtest, paper_trading, signals as signals_router, sync as sync_router
from services.sync import scheduler
from services.seed import load_seeds
from services.signals.books import bootstrap_books

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await load_seeds()
    # Auto-create one House Book per REGISTERED signal + migrate legacy
    # simulated_bets.book_type='house_*pct' rows into the new book_id model.
    # Idempotent; safe on every cold start.
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        await bootstrap_books(db)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="Goalcast API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(fixtures.router, prefix="/api")
app.include_router(odds.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")
app.include_router(paper_trading.router, prefix="/api")
app.include_router(signals_router.router, prefix="/api")
app.include_router(sync_router.router, prefix="/api")
