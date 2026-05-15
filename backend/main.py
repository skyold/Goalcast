from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db
from routers import fixtures, odds, history, sync as sync_router
from services.sync import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)

app = FastAPI(title="Goalcast API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fixtures.router, prefix="/api")
app.include_router(odds.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(sync_router.router, prefix="/api")
