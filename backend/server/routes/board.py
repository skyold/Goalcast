from pathlib import Path
import json
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/board", tags=["board"])

_MATCHES_DIR = Path(__file__).resolve().parents[2] / "data" / "matches"

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
            _flatten_metadata(data)
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


def _flatten_metadata(data: dict) -> None:
    md = data.get("metadata")
    if isinstance(md, dict):
        for k, v in md.items():
            if k == "league" and isinstance(v, dict):
                data["league_name"] = v.get("name", v.get("short_code", ""))
                data["league_id"] = v.get("id")
            elif k not in data:
                data[k] = v

    orch = data.get("orchestrator")
    if isinstance(orch, dict):
        league_val = orch.get("league", "")
        if isinstance(league_val, dict):
            data["league_name"] = data.get("league_name") or league_val.get("name", "")
        elif league_val and not data.get("league_name"):
            data["league_name"] = str(league_val)
        for k in ("home_team", "away_team", "kickoff_time"):
            if k not in data or not data.get(k):
                v = orch.get(k)
                if v:
                    data[k] = v


@router.post("/matches/{match_id}/refresh/{source}")
async def refresh_match_source(match_id: str, source: str) -> dict:
    """实时从指定 provider 获取数据并写入 raw_data.{source}。"""
    match_file = _MATCHES_DIR / f"{match_id}.json"
    if not match_file.exists():
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found")
    try:
        record: dict = json.loads(match_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to read match file: {e}") from e

    fixture_id = (
        (record.get("metadata") or {}).get("fixture_id")
        or (record.get("orchestrator") or {}).get("fixture_id")
    )
    if not fixture_id:
        raise HTTPException(status_code=400, detail="fixture_id not found in match record")

    if source == "oddalerts":
        from agents.core.data_collector import collect_oddalerts
        meta = record.get("metadata") or record.get("orchestrator") or {}
        provider_ids: dict = meta.get("provider_ids") or {}
        oa_fixture_id: int | None = provider_ids.get("oddalerts") or meta.get("oa_fixture_id")

        # 旧版记录没有 provider_ids，尝试用 fixture_mapper 实时查找
        if not oa_fixture_id:
            try:
                from datetime import datetime
                from provider.oddalerts.client import OddAlertsProvider
                from provider.oddalerts.fixture_mapper import find_oddalerts_fixture_id
                home_team = meta.get("home_team", "")
                away_team = meta.get("away_team", "")
                kickoff_str = meta.get("kickoff_time", "")
                kickoff_unix: int | None = None
                if kickoff_str:
                    try:
                        kickoff_unix = int(datetime.fromisoformat(kickoff_str.replace("Z", "+00:00")).timestamp())
                    except Exception:
                        pass
                _oa = OddAlertsProvider()
                if await _oa.is_available():
                    oa_fixture_id = await find_oddalerts_fixture_id(
                        _oa, int(fixture_id), home_team, away_team, kickoff_unix
                    )
                await _oa.close()
            except Exception:
                pass

        if not oa_fixture_id:
            raise HTTPException(
                status_code=404,
                detail="未找到对应的 OddAlerts fixture_id，该比赛可能未被 OddAlerts 收录",
            )
        data = await collect_oddalerts(int(oa_fixture_id))
        if not data:
            raise HTTPException(
                status_code=503,
                detail="OddAlerts 数据获取失败，请检查 API Key 或网络连接",
            )
        raw_data = record.get("raw_data") or {}
        raw_data[source] = data
        record["raw_data"] = raw_data
        match_file.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"source": source, "data": data}
    else:
        raise HTTPException(
            status_code=400,
            detail=f"'{source}' 暂不支持通过 Board API 实时刷新，请通过流水线更新",
        )
