import json
import pytest
from pathlib import Path
from unittest.mock import patch


def test_get_active_providers_returns_enabled_only(tmp_path):
    cfg = {
        "analyst": {"enabled": True},
        "schedule": {"interval_hours": 1},
        "providers": {
            "oddalerts": {"enabled": True},
            "sportmonks": {"enabled": False},
            "footystats": {"enabled": False},
            "understat": {"enabled": False},
        },
    }
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import get_active_providers
        providers = get_active_providers()

    names = [p.name for p in providers]
    assert names == ["oddalerts"]


def test_set_provider_enabled_persists(tmp_path):
    cfg = {
        "analyst": {"enabled": True},
        "schedule": {"interval_hours": 1},
        "providers": {"oddalerts": {"enabled": False}},
    }
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider import registry
        registry.set_provider_enabled("oddalerts", True)
        result = json.loads(cfg_file.read_text())

    assert result["providers"]["oddalerts"]["enabled"] is True


def test_is_analyst_enabled(tmp_path):
    cfg = {"analyst": {"enabled": False}, "schedule": {"interval_hours": 1}, "providers": {}}
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import is_analyst_enabled
        assert is_analyst_enabled() is False


def test_get_schedule_hours(tmp_path):
    cfg = {"analyst": {"enabled": True}, "schedule": {"interval_hours": 3}, "providers": {}}
    cfg_file = tmp_path / "providers.json"
    cfg_file.write_text(json.dumps(cfg), encoding="utf-8")

    with patch("provider.registry._CONFIG_PATH", cfg_file):
        from provider.registry import get_schedule_hours
        assert get_schedule_hours() == 3
