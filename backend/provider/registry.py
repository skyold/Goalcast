from __future__ import annotations

import json
from pathlib import Path

from provider.base import BaseProvider

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "providers.json"


def _load() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "analyst": {"enabled": True},
            "schedule": {"interval_hours": 1},
            "providers": {},
        }


def _save(cfg: dict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def get_config() -> dict:
    return _load()


def get_active_providers() -> list[BaseProvider]:
    cfg = _load()
    pcfg = cfg.get("providers", {})
    active: list[BaseProvider] = []
    if pcfg.get("oddalerts", {}).get("enabled", False):
        from provider.oddalerts.client import OddAlertsProvider
        active.append(OddAlertsProvider())
    if pcfg.get("sportmonks", {}).get("enabled", False):
        from provider.sportmonks.client import SportmonksProvider
        active.append(SportmonksProvider())
    if pcfg.get("footystats", {}).get("enabled", False):
        from provider.footystats.client import FootyStatsProvider
        active.append(FootyStatsProvider())
    if pcfg.get("understat", {}).get("enabled", False):
        from provider.understat.client import UnderstatProvider
        active.append(UnderstatProvider())
    return active


def is_analyst_enabled() -> bool:
    return _load().get("analyst", {}).get("enabled", True)


def get_schedule_hours() -> int:
    return int(_load().get("schedule", {}).get("interval_hours", 1))


def set_provider_enabled(name: str, enabled: bool) -> None:
    cfg = _load()
    cfg.setdefault("providers", {}).setdefault(name, {})["enabled"] = enabled
    _save(cfg)


def set_analyst_enabled(enabled: bool) -> None:
    cfg = _load()
    cfg.setdefault("analyst", {})["enabled"] = enabled
    _save(cfg)


def set_schedule_hours(hours: int) -> None:
    cfg = _load()
    cfg.setdefault("schedule", {})["interval_hours"] = hours
    _save(cfg)
