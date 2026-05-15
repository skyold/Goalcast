from fastapi import APIRouter, BackgroundTasks
from services.sync import full_sync

router = APIRouter()

@router.post("/sync/trigger")
async def trigger_sync(bg: BackgroundTasks):
    bg.add_task(full_sync)
    return {"started": True}
