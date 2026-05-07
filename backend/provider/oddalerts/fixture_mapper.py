"""
OddAlerts fixture ID 映射器。

OddAlerts 与 SportMonks 使用不同的 fixture_id 体系，此模块负责：
1. 优先查本地缓存（data/oddalerts_fixture_map.json）
2. 尝试同 ID 直查（部分赛事两方 ID 相同）
3. 按队名 + 开赛时间扫描 dropping odds 搜索匹配
4. 缓存结果（含 None，避免重复搜索同一场失败赛事）
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from utils.normalize import normalize_team_name as _normalize

if TYPE_CHECKING:
    from provider.oddalerts.client import OddAlertsProvider

logger = logging.getLogger(__name__)

_MAP_FILE = Path(__file__).resolve().parents[2] / "data" / "oddalerts_fixture_map.json"
_SEARCH_PAGES = 5       # 最多扫描几页 dropping odds（每页 ~250 条）
_TIME_TOLERANCE = 7200  # 开赛时间允许误差（秒），2 小时


# ─── 缓存 IO ──────────────────────────────────────────────────────────────────

def _load_map() -> dict:
    if _MAP_FILE.exists():
        try:
            return json.loads(_MAP_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_map(m: dict) -> None:
    _MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    _MAP_FILE.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── 名称归一化 ────────────────────────────────────────────────────────────────

def _names_match(oa_fixture_name: str, home: str, away: str) -> bool:
    """
    判断 OddAlerts fixture_name 是否对应给定的主客队。

    策略：
    - OddAlerts 格式通常为 "Home Team vs Away Team"
    - 先分割 " vs " 做精确归一化比较
    - 退而求其次：检查双方名称的前 6 个归一化字符是否都出现在 fixture_name 中
    """
    if not oa_fixture_name:
        return False

    hn = _normalize(home)
    an = _normalize(away)
    fn = _normalize(oa_fixture_name)

    # 分割尝试精确对比
    if " vs " in oa_fixture_name.lower():
        parts = oa_fixture_name.lower().split(" vs ", 1)
        oa_home_n = _normalize(parts[0])
        oa_away_n = _normalize(parts[1])
        if oa_home_n == hn and oa_away_n == an:
            return True
        # 允许前缀匹配（截取前 8 字符）
        h6, a6 = hn[:8], an[:8]
        if (oa_home_n.startswith(h6) or h6.startswith(oa_home_n[:8])) and \
           (oa_away_n.startswith(a6) or a6.startswith(oa_away_n[:8])):
            return True

    # 兜底：双方名称的前 6 字符都在 fixture_name 中出现
    if len(hn) >= 4 and len(an) >= 4:
        return hn[:6] in fn and an[:6] in fn

    return False


# ─── 主函数 ───────────────────────────────────────────────────────────────────

async def find_oddalerts_fixture_id(
    provider: "OddAlertsProvider",
    sportmonks_id: int,
    home_team: str = "",
    away_team: str = "",
    kickoff_unix: int | None = None,
) -> int | None:
    """
    返回与 SportMonks fixture_id 对应的 OddAlerts fixture_id。
    若找不到则返回 None（并缓存 None 以避免重复搜索）。
    """
    cache = _load_map()
    key = str(sportmonks_id)

    if key in cache:
        cached = cache[key]
        logger.debug("fixture_mapper: cache hit %s → %s", key, cached)
        return cached  # 可能是 None（上次搜索未找到）

    # ── 策略 1：同 ID 尝试 ────────────────────────────────────────────────────
    fixture = await provider.get_fixture(sportmonks_id)
    if isinstance(fixture, dict) and fixture.get("id"):
        logger.info("fixture_mapper: 同 ID 命中 %d", sportmonks_id)
        cache[key] = sportmonks_id
        _save_map(cache)
        return sportmonks_id

    # ── 策略 2：扫描 dropping odds 按名称 + 时间匹配 ──────────────────────────
    if not home_team or not away_team:
        logger.warning("fixture_mapper: 缺少队名，无法搜索 OddAlerts fixture_id (sm=%d)", sportmonks_id)
        cache[key] = None
        _save_map(cache)
        return None

    logger.info(
        "fixture_mapper: 搜索 OddAlerts fixture_id for %s vs %s (sm_id=%d)",
        home_team, away_team, sportmonks_id,
    )

    for page in range(1, _SEARCH_PAGES + 1):
        resp = await provider.get_dropping_odds(page=page)
        if not isinstance(resp, dict):
            break
        items = resp.get("data", [])
        if not items:
            break

        seen_fixture_ids: set[int] = set()
        for item in items:
            oa_fid = item.get("fixture_id")
            if oa_fid is None or oa_fid in seen_fixture_ids:
                continue
            seen_fixture_ids.add(oa_fid)

            oa_name = item.get("fixture_name", "")
            oa_unix = item.get("unix")

            if not _names_match(oa_name, home_team, away_team):
                continue

            if kickoff_unix and oa_unix:
                if abs(int(oa_unix) - kickoff_unix) > _TIME_TOLERANCE:
                    continue

            logger.info(
                "fixture_mapper: 找到匹配（dropping odds）！'%s' → oa_fixture_id=%d (page=%d)",
                oa_name, oa_fid, page,
            )
            cache[key] = oa_fid
            _save_map(cache)
            return oa_fid

        logger.debug("fixture_mapper: dropping odds page %d 未找到，继续...", page)

    # ── 策略 3：扫描 trends 端点（含未来赛事概率）──────────────────────────────
    logger.debug("fixture_mapper: 尝试 trends 端点扫描 %s vs %s", home_team, away_team)
    for market in ("homeWin", "awayWin", "btts"):
        for page in range(1, 3):  # trends 数据量大，扫前 2 页即可
            resp = await provider.get_trends(market, page=page)  # type: ignore[arg-type]
            if not isinstance(resp, dict):
                break
            items = resp.get("data", [])
            if not items:
                break

            for item in items:
                oa_fid = item.get("id")
                if oa_fid is None:
                    continue
                oa_home = item.get("home_name", "")
                oa_away = item.get("away_name", "")
                fixture_name = f"{oa_home} vs {oa_away}"
                if not _names_match(fixture_name, home_team, away_team):
                    continue

                oa_unix = item.get("unix")
                if kickoff_unix and oa_unix:
                    if abs(int(oa_unix) - kickoff_unix) > _TIME_TOLERANCE:
                        continue

                logger.info(
                    "fixture_mapper: 找到匹配（trends/%s）！'%s' → oa_fixture_id=%d",
                    market, fixture_name, oa_fid,
                )
                cache[key] = oa_fid
                _save_map(cache)
                return oa_fid

    logger.warning(
        "fixture_mapper: 未找到 OddAlerts fixture_id for %s vs %s (sm=%d)",
        home_team, away_team, sportmonks_id,
    )
    cache[key] = None
    _save_map(cache)
    return None
