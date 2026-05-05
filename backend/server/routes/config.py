from pathlib import Path
import json
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["config"])

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


@router.get("")
async def get_config() -> dict:
    if _CONFIG_PATH.exists():
        try:
            return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "app": {"name": "Goalcast", "subtitle": "Football Quant System"},
        "modules": {"agents": True, "board": True, "tokens": True, "chat": True, "logs": True},
        "agents": {"clusters": []},
        "board": {"tabs": []},
    }
