"""
运行时动态联赛配置。
将活跃联赛列表持久化到 data/active_leagues.json，
Orchestrator 每次拉取前重新读取，实现无重启增删联赛。

CLI 操作（通过 docker exec）：
    python main.py leagues add 西甲
    python main.py leagues remove 英超
    python main.py leagues list
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "data"
CONFIG_FILE = CONFIG_DIR / "active_leagues.json"

_CST = timezone(timedelta(hours=8))


def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _read() -> list[str]:
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return []
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("leagues", [])
    except (json.JSONDecodeError, IOError) as exc:
        logger.warning("[LeagueConfig] 读取失败: %s", exc)
        return []


def _write(leagues: list[str]) -> None:
    _ensure_dir()
    data = {
        "leagues": leagues,
        "updated_at": datetime.now(_CST).isoformat(),
    }
    CONFIG_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def init(leagues: list[str]) -> None:
    """初始化写入活跃联赛（只在启动时调用，不会覆盖已有配置）。"""
    _ensure_dir()
    if CONFIG_FILE.exists():
        existing = _read()
        if existing:
            logger.info(
                "[LeagueConfig] 已有活跃联赛配置: %s，跳过初始化", existing
            )
            return
    _write(leagues)
    logger.info("[LeagueConfig] 初始化活跃联赛: %s", leagues)


def get_active() -> list[str]:
    """获取当前活跃联赛列表。"""
    return _read()


def add(name: str) -> bool:
    """添加一个联赛，返回是否实际新增。"""
    current = _read()
    if name in current:
        logger.info("[LeagueConfig] 联赛已存在: %s", name)
        return False
    current.append(name)
    _write(current)
    logger.info("[LeagueConfig] 已添加联赛: %s", name)
    return True


def remove(name: str) -> bool:
    """移除一个联赛，返回是否实际移除。"""
    current = _read()
    if name not in current:
        logger.info("[LeagueConfig] 联赛不存在: %s", name)
        return False
    current.remove(name)
    _write(current)
    logger.info("[LeagueConfig] 已移除联赛: %s", name)
    return True


def list_leagues() -> list[str]:
    """返回当前活跃联赛列表（与 get_active 相同，供 CLI 使用）。"""
    return _read()
