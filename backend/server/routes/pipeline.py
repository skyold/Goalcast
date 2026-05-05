from pathlib import Path
import json
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])

_CST = timezone(timedelta(hours=8))
_MATCHES_DIR = Path(__file__).resolve().parents[2] / "data" / "matches"
_LEAGUES_FILE = Path(__file__).resolve().parents[2] / "config" / "sportmonks_leagues.json"
_ACTIVE_FILE = Path(__file__).resolve().parents[2] / "data" / "active_leagues.json"
_TRIGGER_FILE = Path(__file__).resolve().parents[2] / "data" / "trigger.json"


def _read_active_leagues() -> list[str]:
    if not _ACTIVE_FILE.exists():
        return []
    try:
        data = json.loads(_ACTIVE_FILE.read_text(encoding="utf-8"))
        return data.get("leagues", [])
    except Exception:
        return []


@router.get("/leagues")
async def get_leagues() -> dict:
    active = _read_active_leagues()
    active_set = set(active)
    available = []
    if _LEAGUES_FILE.exists():
        try:
            all_leagues = json.loads(_LEAGUES_FILE.read_text(encoding="utf-8"))
            seen: set[str] = set()
            for lid, info in all_leagues.items():
                cn = info.get("chinese_name", info.get("name", ""))
                if cn in seen:
                    continue
                seen.add(cn)
                available.append({
                    "id": info.get("id"),
                    "chinese_name": cn,
                    "name": info.get("name", ""),
                    "active": cn in active_set,
                })
        except Exception:
            pass
    available.sort(key=lambda x: x["chinese_name"])
    return {"available": available, "active_count": len(active)}


@router.post("/leagues")
async def update_leagues(body: dict) -> dict:
    leagues = body.get("leagues", [])
    if not isinstance(leagues, list):
        leagues = []
    _ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "leagues": leagues,
        "updated_at": datetime.now(_CST).isoformat(),
    }
    _ACTIVE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"active": leagues, "message": "已更新活跃联赛"}


@router.post("/trigger")
async def trigger_pipeline(body: dict = None) -> dict:
    _TRIGGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    force = False
    if body and body.get("force"):
        force = True
    payload = {"force": force}
    _TRIGGER_FILE.write_text(json.dumps(payload), encoding="utf-8")
    return {"message": "已触发比赛拉取"}


@router.get("/matches")
async def get_matches(
    date_from: str = Query(default=None),
    date_to: str = Query(default=None),
) -> dict:
    now = datetime.now(_CST)
    if not date_from:
        date_from = (now - timedelta(days=2)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = (now + timedelta(days=3)).strftime("%Y-%m-%d")

    items = []
    if _MATCHES_DIR.exists():
        for fp in sorted(_MATCHES_DIR.glob("*.json")):
            try:
                record = json.loads(fp.read_text(encoding="utf-8"))
            except Exception:
                continue
            md = record.get("metadata", {})
            orch = record.get("orchestrator", {})
            if isinstance(md, dict):
                league = md.get("league", {})
                league_name = league.get("name", "") if isinstance(league, dict) else str(league) if league else ""
                home_team = md.get("home_team", "")
                away_team = md.get("away_team", "")
                kickoff_time = md.get("kickoff_time", "")
                fixture_id = md.get("fixture_id")
            else:
                league_name = ""
                home_team = ""
                away_team = ""
                kickoff_time = ""
                fixture_id = None
            # 回退到 orchestrator（兼容旧版 match_store 格式）
            if not league_name and isinstance(orch, dict):
                league_val = orch.get("league", "")
                if isinstance(league_val, dict):
                    league_name = league_val.get("name", "")
                elif league_val:
                    league_name = str(league_val)
            if not home_team and isinstance(orch, dict):
                home_team = orch.get("home_team", "")
            if not away_team and isinstance(orch, dict):
                away_team = orch.get("away_team", "")
            if not kickoff_time and isinstance(orch, dict):
                kickoff_time = orch.get("kickoff_time", "")
            status = record.get("status", "unknown")
            state = record.get("state", {})
            analysis = record.get("analysis", {}) or {}
            trading = record.get("trading", {}) or {}
            review = record.get("review", {}) or {}

            kt_str = str(kickoff_time) if kickoff_time else ""
            if kt_str:
                kt_date = kt_str[:10]
                if kt_date < date_from or kt_date > date_to:
                    continue
                # 只显示还没有开始的比赛
                try:
                    kt_dt = datetime.fromisoformat(kt_str)
                    if kt_dt.tzinfo is None:
                        kt_dt = kt_dt.replace(tzinfo=_CST)
                    if kt_dt < now:
                        continue
                except (ValueError, TypeError):
                    pass

            item = {
                "match_id": record.get("match_id", fp.stem),
                "fixture_id": fixture_id,
                "home_team": home_team,
                "away_team": away_team,
                "league_name": league_name,
                "kickoff_time": kt_str,
                "status": status,
                "state": state,
            }
            if isinstance(analysis, dict) and analysis:
                xg_src = analysis
                if not xg_src.get("home_xg") and not xg_src.get("away_xg"):
                    v4 = xg_src.get("v4.0", {})
                    if isinstance(v4, dict) and (v4.get("home_xg") or v4.get("away_xg")):
                        xg_src = v4
                if not xg_src.get("home_xg") and not xg_src.get("away_xg"):
                    pm = analysis.get("predictive_metrics", {})
                    if isinstance(pm, dict):
                        xg_src = pm
                item["home_xg"] = xg_src.get("home_xg")
                item["away_xg"] = xg_src.get("away_xg")
                item["total_xg"] = xg_src.get("total_xg") or xg_src.get("xg_difference")

                probs_src = analysis
                for sub in ["v4.0", "predictive_metrics"]:
                    if not probs_src.get("fulltime_result_probabilities"):
                        candidate = probs_src.get(sub, {})
                        if isinstance(candidate, dict) and candidate.get("fulltime_result_probabilities"):
                            probs_src = candidate
                            break
                probs = probs_src.get("fulltime_result_probabilities")
                if isinstance(probs, dict):
                    vals = [v for v in probs.values() if isinstance(v, (int, float))]
                    if vals and sum(vals) > 1.1:
                        probs = {k: round(v / 100, 4) for k, v in probs.items() if isinstance(v, (int, float))}
                    item["result_probs"] = probs

                conf_src = analysis
                for sub in ["v4.0", "predictive_metrics"]:
                    if conf_src.get("confidence") is None:
                        candidate = conf_src.get(sub, {})
                        if isinstance(candidate, dict) and candidate.get("confidence") is not None:
                            conf_src = candidate
                            break
                item["confidence"] = conf_src.get("confidence")

                ah_src = analysis
                for sub in ["v4.0", "predictive_metrics"]:
                    if not ah_src.get("ah_recommendation"):
                        candidate = ah_src.get(sub, {})
                        if isinstance(candidate, dict) and candidate.get("ah_recommendation"):
                            ah_src = candidate
                            break
                ah = ah_src.get("ah_recommendation")
                if isinstance(ah, dict):
                    item["recommendation"] = f"{ah.get('side','')} {ah.get('line','')}".strip() or None
                else:
                    item["recommendation"] = ah
            if isinstance(trading, dict) and trading:
                results = trading.get("results", {})
                if isinstance(results, dict):
                    item["ev"] = results.get("ev")
            if isinstance(review, dict) and review:
                item["verdict"] = review.get("verdict")
            items.append(item)

    items.sort(key=lambda x: x.get("kickoff_time", ""))
    return {
        "items": items,
        "total": len(items),
        "date_range": {"from": date_from, "to": date_to},
    }
