from pathlib import Path
import json
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])

_CST = timezone(timedelta(hours=8))
_ROLES_DIR = Path(__file__).resolve().parents[2] / "agents" / "roles"
_MATCHES_DIR = Path(__file__).resolve().parents[2] / "data" / "matches"

CLUSTER_MAP = {
    "orchestrator": "prediction",
    "analyst": "prediction",
    "trader": "prediction",
    "reviewer": "prediction",
    "reporter": "prediction",
    "backtester": "backtester",
}

ROLE_DESCRIPTIONS = {
    "orchestrator": "赛程编排与任务分发",
    "analyst": "泊松 xG 量化分析与概率计算",
    "trader": "亚盘/大小球交易执行与注额分配",
    "reviewer": "交易合理性审核与赛后复盘",
    "reporter": "赛事洞察 Markdown 报告生成",
    "backtester": "历史回测与 ROI/Hit Rate 评估",
}


def _scan_roles() -> list[str]:
    roles = []
    for cluster_dir in _ROLES_DIR.iterdir():
        if not cluster_dir.is_dir() or cluster_dir.name.startswith("_"):
            continue
        if cluster_dir.name == "prediction":
            for role_dir in cluster_dir.iterdir():
                if role_dir.is_dir() and not role_dir.name.startswith("_"):
                    roles.append(role_dir.name)
        else:
            if (cluster_dir / "IDENTITY.md").exists():
                roles.append(cluster_dir.name)
    return roles


def _read_identity(role: str) -> str:
    candidates = [
        _ROLES_DIR / "prediction" / role / "IDENTITY.md",
        _ROLES_DIR / role / "IDENTITY.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text(encoding="utf-8").strip()[:100]
    return ""


def _count_matches_by_status(status_list: list[str]) -> int:
    if not _MATCHES_DIR.exists():
        return 0
    count = 0
    for f in _MATCHES_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") in status_list:
                count += 1
        except Exception:
            pass
    return count


@router.get("/agents/status")
async def get_agent_status() -> list[dict]:
    roles = _scan_roles()
    now = datetime.now(_CST).isoformat()
    result = []
    for role in roles:
        identity = _read_identity(role)
        cluster = CLUSTER_MAP.get(role, "other")
        state_counts = {
            "pending": _count_matches_by_status(["pending"]),
        }
        active_count = 0
        if role == "analyst":
            active_count = _count_matches_by_status(["pending", "analyzing"])
        elif role == "trader":
            active_count = _count_matches_by_status(["analyzed", "trading", "feedback"])
        elif role == "reviewer":
            active_count = _count_matches_by_status(["traded", "reviewing"])
        elif role == "reporter":
            active_count = _count_matches_by_status(["reviewed", "reported"])
        elif role == "backtester":
            active_count = _count_matches_by_status(["reported"])

        result.append({
            "agent_id": f"goalcast-{role}",
            "role": role,
            "cluster": cluster,
            "status": "idle" if active_count == 0 else "running",
            "task": f"{active_count} matches queued" if active_count > 0 else "Idle",
            "description": ROLE_DESCRIPTIONS.get(role, ""),
            "last_active": now,
        })
    return result


@router.get("/agents/{agent_id}/detail")
async def get_agent_detail(agent_id: str) -> dict:
    role = agent_id.replace("goalcast-", "", 1)
    now = datetime.now(_CST).isoformat()
    cluster = CLUSTER_MAP.get(role, "other")

    def _read_file(role: str, filename: str) -> str:
        candidates = [
            _ROLES_DIR / "prediction" / role / filename,
            _ROLES_DIR / role / filename,
        ]
        for p in candidates:
            if p.exists():
                return p.read_text(encoding="utf-8")
        return ""

    def _read_skills(role: str) -> list[dict]:
        skills_dir = _ROLES_DIR / "prediction" / role / "skills"
        if not skills_dir.exists():
            skills_dir = _ROLES_DIR / role / "skills"
        if not skills_dir.exists():
            return []
        result = []
        for f in skills_dir.glob("SKILL.md"):
            result.append({"name": f.parent.name, "content": f.read_text(encoding="utf-8")[:200]})
        skills_json = skills_dir / "skills.jsonc"
        if skills_json.exists():
            try:
                config = json.loads(skills_json.read_text(encoding="utf-8"))
                for s in config.get("skills", []):
                    result.append({"name": s.get("name", "unknown"), "content": json.dumps(s, ensure_ascii=False)[:200]})
            except Exception:
                pass
        return result

    identity = _read_file(role, "IDENTITY.md")
    agents_md = _read_file(role, "AGENTS.md")
    soul_md = _read_file(role, "SOUL.md")
    memory_md = _read_file(role, "MEMORY.md")
    tools_md = _read_file(role, "TOOLS.md")

    tool_reg = _ROLES_DIR / "prediction" / role / "tool-registry.jsonc"
    if not tool_reg.exists():
        tool_reg = _ROLES_DIR / role / "tool-registry.jsonc"
    tools = []
    if tool_reg.exists():
        try:
            reg = json.loads(tool_reg.read_text(encoding="utf-8"))
            for t in reg.get("mcp", []) + reg.get("builtin", []):
                tools.append({"name": t if isinstance(t, str) else t.get("name", str(t)), "description": ""})
        except Exception:
            pass

    active_count = 0
    if role == "analyst":
        active_count = _count_matches_by_status(["pending", "analyzing"])
    elif role == "trader":
        active_count = _count_matches_by_status(["analyzed", "trading", "feedback"])
    elif role == "reviewer":
        active_count = _count_matches_by_status(["traded", "reviewing"])
    elif role == "reporter":
        active_count = _count_matches_by_status(["reviewed", "reported"])

    return {
        "state": {
            "agent_id": agent_id,
            "role": role,
            "cluster": cluster,
            "status": "running" if active_count > 0 else "idle",
            "task": f"{active_count} matches queued" if active_count > 0 else "Idle",
            "last_active": now,
        },
        "components": {
            "IDENTITY.md": identity,
            "AGENTS.md": agents_md,
            "SOUL.md": soul_md,
            "MEMORY.md": memory_md,
            "TOOLS.md": tools_md,
            "skills": _read_skills(role),
        },
        "tools": tools,
    }


@router.get("/pipelines/status")
async def get_pipeline_status() -> list[dict]:
    pipeline_steps = ["pending", "analyzed", "traded", "reviewed", "reported"]
    totals = {
        "pending": _count_matches_by_status(["pending"]),
        "analyzing": _count_matches_by_status(["analyzing"]),
        "analyzed": _count_matches_by_status(["analyzed"]),
        "trading": _count_matches_by_status(["trading"]),
        "traded": _count_matches_by_status(["traded"]),
        "reviewing": _count_matches_by_status(["reviewing"]),
        "reviewed": _count_matches_by_status(["reviewed"]),
        "reported": _count_matches_by_status(["reported"]),
        "rejected": _count_matches_by_status(["rejected"]),
        "completed": _count_matches_by_status(["completed"]),
    }
    active = totals["analyzing"] + totals["trading"] + totals["reviewing"]
    return [
        {
            "pipeline": "rd",
            "mode": "full",
            "status": "running" if active > 0 else "idle",
            "current_step": "analyst" if totals["analyzing"] > 0
                else "trader" if totals["trading"] > 0
                else "reviewer" if totals["reviewing"] > 0
                else "idle",
            "round": 1,
            "total": sum(totals.values()),
            "detail": totals,
        }
    ]
