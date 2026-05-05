from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/board", tags=["board"])

_BOARD_BASE = Path(__file__).resolve().parents[2] / "data"


def _safe_subpath(base: Path, *parts: str) -> Path:
    resolved_base = base.resolve()
    candidate = (base / Path(*parts)).resolve()
    if not str(candidate).startswith(str(resolved_base)):
        raise HTTPException(status_code=400, detail="Invalid path: traversal not allowed")
    return candidate


@router.get("/{dir}")
async def get_board_list(
    dir: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    dir_path = _safe_subpath(_BOARD_BASE, dir)
    if not dir_path.exists() or not dir_path.is_dir():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}

    items: list[dict] = []
    for f in sorted(dir_path.glob("*.json")):
        try:
            data: dict = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.name
            items.append(data)
        except Exception:
            pass

    total = len(items)
    start = (page - 1) * page_size
    return {
        "items": items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{dir}/{filename}")
async def get_board_item(dir: str, filename: str) -> dict:
    file_path = _safe_subpath(_BOARD_BASE, dir, filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"{dir}/{filename} not found")
    try:
        data: dict = json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read {filename}: {e}") from e
    data["_filename"] = file_path.name
    return data
