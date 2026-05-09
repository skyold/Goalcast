"""
统一 Match Store。
每场比赛一个 JSON 文件，单一写入路径，无双写。

状态转换：pending → collected → analyzed / error
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config.settings import DATA_DIR

logger = logging.getLogger(__name__)

MATCHES_DIR = DATA_DIR / "matches"
_CST = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(_CST).isoformat()


def generate_match_id() -> str:
    ts = datetime.now(_CST).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:6].upper()
    return f"MC-{ts}-{uid}"


def _write(record: dict) -> None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    fp = MATCHES_DIR / f"{record['match_id']}.json"
    fp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def save(record: dict) -> str:
    """写入新比赛记录。record 必须包含 match_id 字段。"""
    _write(record)
    logger.info("[MatchStore] 保存: %s", record["match_id"])
    return record["match_id"]


def get(match_id: str) -> dict | None:
    fp = MATCHES_DIR / f"{match_id}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("[MatchStore] JSON 损坏: %s", match_id)
        return None


def update(match_id: str, fields: dict) -> None:
    """局部更新 match 的顶层字段。fields 是要合并的键值对。"""
    record = get(match_id)
    if record is None:
        logger.warning("[MatchStore] 更新目标不存在: %s", match_id)
        return
    record.update(fields)
    _write(record)
    logger.debug("[MatchStore] 更新: %s fields=%s", match_id, list(fields.keys()))


def list_matches(
    league: str | None = None,
    date: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """返回所有 match，支持按 league/date/status 过滤。date 格式 YYYY-MM-DD。"""
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for fp in sorted(MATCHES_DIR.glob("MC-*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if status and record.get("status") != status:
            continue

        meta = record.get("metadata", {})
        if league and meta.get("league", "") != league:
            continue
        if date:
            kt = str(meta.get("kickoff_time", ""))
            if not kt.startswith(date):
                continue

        results.append(record)
    return results


def exists_for_fixture(provider_name: str, fixture_id: int) -> str | None:
    """如果已存在对应 fixture 的 match，返回其 match_id，否则返回 None。"""
    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        pids = record.get("metadata", {}).get("provider_ids", {})
        if pids.get(provider_name) == fixture_id:
            return record.get("match_id")
    return None
