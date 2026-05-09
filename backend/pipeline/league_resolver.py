"""
联赛名称模糊匹配，将用户输入映射到各 provider 的联赛 ID。
替代旧的 LLM 匹配方案。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from thefuzz import process

logger = logging.getLogger(__name__)

_SM_LEAGUES_PATH = Path(__file__).resolve().parent.parent / "config" / "sportmonks_leagues.json"
_OA_LEAGUES_PATH = Path(__file__).resolve().parent.parent / "config" / "oddalerts_leagues.json"


def _load_sm_leagues() -> dict:
    if not _SM_LEAGUES_PATH.exists():
        return {}
    try:
        return json.loads(_SM_LEAGUES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return {}


def _load_oa_mapping() -> dict[str, int | None]:
    if not _OA_LEAGUES_PATH.exists():
        return {}
    try:
        cfg = json.loads(_OA_LEAGUES_PATH.read_text(encoding="utf-8"))
        return cfg.get("_sportmonks_to_oddalerts", {})
    except (json.JSONDecodeError, IOError):
        return {}


def resolve_league_ids(
    league_names: list[str],
    score_cutoff: int = 70,
) -> dict[str, list[int]]:
    """
    将联赛名称列表模糊匹配到各 provider 的联赛 ID。

    Args:
        league_names: 用户输入的联赛名称列表，支持中英文
        score_cutoff: 最低匹配分数 (0-100)，低于此值视为未匹配

    Returns:
        {
            "sportmonks": [271, 8],
            "oddalerts":  [4, 2],
        }
    """
    sm_dict = _load_sm_leagues()
    if not sm_dict:
        return {"sportmonks": [], "oddalerts": []}

    # 建立候选名称 → SM ID 的映射
    candidates: dict[str, int] = {}
    for key, info in sm_dict.items():
        sm_id = info.get("id") if isinstance(info, dict) else None
        if sm_id is None:
            continue
        name = info.get("name", "") if isinstance(info, dict) else ""
        cn = info.get("chinese_name", "") if isinstance(info, dict) else ""
        if name:
            candidates[name] = sm_id
        if cn:
            candidates[cn] = sm_id

    if not candidates:
        return {"sportmonks": [], "oddalerts": []}

    oa_mapping = _load_oa_mapping()
    sm_ids: list[int] = []
    oa_ids: list[int] = []

    for query in league_names:
        if str(query).isdigit():
            sm_id = int(query)
            sm_ids.append(sm_id)
            oa_id = oa_mapping.get(str(sm_id))
            if isinstance(oa_id, int):
                oa_ids.append(oa_id)
            continue

        match = process.extractOne(query, candidates.keys(), score_cutoff=score_cutoff)
        if match is None:
            logger.warning("[LeagueResolver] 未匹配: %r", query)
            continue

        matched_name, score, _ = match
        sm_id = candidates[matched_name]
        logger.debug("[LeagueResolver] %r → %r (score=%d, sm_id=%d)", query, matched_name, score, sm_id)
        if sm_id not in sm_ids:
            sm_ids.append(sm_id)

        oa_id = oa_mapping.get(str(sm_id))
        if isinstance(oa_id, int) and oa_id not in oa_ids:
            oa_ids.append(oa_id)

    return {"sportmonks": sm_ids, "oddalerts": oa_ids}
