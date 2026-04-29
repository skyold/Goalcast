"""
单场比赛的完整生命周期存储。
一场比赛一个 JSON 文件，所有 Agent 的输出都追加到同一个文件。
对齐 yclake 的 hypothesis_store 模式。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MATCHES_DIR = Path(__file__).parent.parent.parent / "data" / "matches"
_CST = timezone(timedelta(hours=8))

_STATUS_MAP = {
    "analysis": "analyzed",
    "trade": "traded",
    "review": "reviewed",
    "post_match": "completed",
}


def now_iso() -> str:
    return datetime.now(_CST).isoformat()


def generate_match_id() -> str:
    ts = datetime.now(_CST).strftime("%Y%m%d-%H%M%S")
    uid = uuid.uuid4().hex[:8].upper()
    return f"MC-{ts}-{uid}"


def save(record: dict) -> str:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    match_id = record["match_id"]
    _write(match_id, record)
    logger.info("[MatchStore] 比赛已保存: %s", match_id)
    return match_id


def load(match_id: str) -> dict | None:
    filepath = MATCHES_DIR / f"{match_id}.json"
    if not filepath.exists():
        return None
    try:
        return json.loads(filepath.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("[MatchStore] 比赛 JSON 损坏: %s", match_id)
        return None


def load_from_file(filepath: str) -> dict | None:
    try:
        return json.loads(Path(filepath).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None


def append_layer(match_id: str, layer_name: str, layer_data: dict) -> None:
    record = load(match_id)
    if record is None:
        return
    record[layer_name] = layer_data
    if layer_name in _STATUS_MAP:
        record["status"] = _STATUS_MAP[layer_name]
    _write(match_id, record)
    logger.info(
        "[MatchStore] 比赛 %s 追加层 %s, 状态 → %s",
        match_id,
        layer_name,
        record["status"],
    )


def update_status(match_id: str, status: str) -> None:
    record = load(match_id)
    if record is None:
        return
    record["status"] = status
    _write(match_id, record)
    logger.info("[MatchStore] 比赛 %s 状态 → %s", match_id, status)


def claim_oldest(status_list: list[str], new_status: str) -> dict | None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[str, dict]] = []

    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            if record.get("status") in status_list:
                prepared = (
                    record.get("orchestrator", {}).get("prepared_at", "")
                    or record.get("created_at", "")
                    or "9999"
                )
                candidates.append((prepared, record))
        except json.JSONDecodeError:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    target = candidates[0][1]
    target["status"] = new_status
    _write(target["match_id"], target)
    logger.info(
        "[MatchStore] 认领比赛 %s: %s → %s",
        target["match_id"], status_list, new_status,
    )
    return target


def list_all(status: str | None = None) -> list[dict]:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for fp in sorted(MATCHES_DIR.glob("MC-*.json")):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if status is None or record.get("status") == status:
            results.append(record)
    return results


def count_by_status(status_list: list[str]) -> int:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for fp in MATCHES_DIR.glob("MC-*.json"):
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
            if record.get("status") in status_list:
                count += 1
        except json.JSONDecodeError:
            continue
    return count


def finalize(match_id: str, report_ref: str = "") -> None:
    record = load(match_id)
    if record is None:
        return
    record["status"] = "reported"
    record["report_ref"] = report_ref
    _write(match_id, record)
    logger.info("[MatchStore] 比赛 %s 已完成 (reported)", match_id)


def _write(match_id: str, record: dict) -> None:
    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    filepath = MATCHES_DIR / f"{match_id}.json"
    filepath.write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
