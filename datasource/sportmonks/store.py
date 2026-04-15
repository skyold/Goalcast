"""Sportmonks JSON 存储层。"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from config.settings import BASE_DIR


class SportmonksStore:
    """负责 Sportmonks 快照与索引文件的 JSON 读写。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else (BASE_DIR / "data" / "cache" / "sportmonks")
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_date_dir(self, date: str) -> Path:
        date_dir = self.base_dir / date
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir

    def read_fixtures(self, date: str) -> List[Dict[str, Any]]:
        path = self.get_date_dir(date) / "fixtures.json"
        if not path.exists():
            return []
        return self._read_json(path, default=[])

    def write_fixtures(self, date: str, fixtures: List[Dict[str, Any]]) -> None:
        self._atomic_write(self.get_date_dir(date) / "fixtures.json", fixtures)

    def read_leagues(self) -> List[Dict[str, Any]]:
        """读取本地保存的全量联赛索引。"""
        path = self.base_dir / "leagues.json"
        if not path.exists():
            return []
        return self._read_json(path, default=[])

    def write_leagues(self, leagues: List[Dict[str, Any]]) -> None:
        """保存全量联赛索引。"""
        self._atomic_write(self.base_dir / "leagues.json", leagues)

    def find_match_dir(self, fixture_id: int, date: Optional[str] = None) -> Optional[Path]:
        candidate_dirs = [self.get_date_dir(date)] if date else [
            child for child in self.base_dir.iterdir() if child.is_dir()
        ]
        suffix = f"__{fixture_id}"
        for date_dir in candidate_dirs:
            for child in date_dir.iterdir():
                if child.is_dir() and child.name.endswith(suffix):
                    return child
        return None

    def read_match(self, fixture_id: int, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        match_dir = self.find_match_dir(fixture_id, date)
        if not match_dir:
            return None
        path = match_dir / "match.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def write_match(
        self,
        fixture_id: int,
        date: str,
        snapshot: Dict[str, Any],
        home_team: str,
        away_team: str,
    ) -> None:
        match_dir = self._get_match_dir(date, fixture_id, home_team, away_team)
        self._atomic_write(match_dir / "match.json", snapshot)

    def read_meta(self, fixture_id: int, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        match_dir = self.find_match_dir(fixture_id, date)
        if not match_dir:
            return None
        path = match_dir / "meta.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def write_meta(self, fixture_id: int, date: str, meta: Dict[str, Any]) -> None:
        match_dir = self.find_match_dir(fixture_id, date)
        if match_dir is None:
            raise FileNotFoundError(f"match directory not found for fixture_id={fixture_id}")
        self._atomic_write(match_dir / "meta.json", meta)

    def write_raw_layer(self, fixture_id: int, date: str, layer: str, payload: Dict[str, Any]) -> None:
        match_dir = self.find_match_dir(fixture_id, date)
        if match_dir is None:
            raise FileNotFoundError(f"match directory not found for fixture_id={fixture_id}")
        raw_dir = match_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        self._atomic_write(raw_dir / f"{layer}.json", payload)

    def read_raw_layer(self, fixture_id: int, date: str, layer: str) -> Optional[Dict[str, Any]]:
        match_dir = self.find_match_dir(fixture_id, date)
        if match_dir is None:
            return None
        path = match_dir / "raw" / f"{layer}.json"
        if not path.exists():
            return None
        return self._read_json(path)

    def _get_match_dir(self, date: str, fixture_id: int, home_team: str, away_team: str) -> Path:
        safe_home = self._slug(home_team)
        safe_away = self._slug(away_team)
        match_dir = self.get_date_dir(date) / f"{safe_home}__{safe_away}__{fixture_id}"
        match_dir.mkdir(parents=True, exist_ok=True)
        return match_dir

    @staticmethod
    def _slug(value: str) -> str:
        return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"

    @staticmethod
    def _read_json(path: Path, default: Optional[Any] = None) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _atomic_write(path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
            json.dump(payload, temp, ensure_ascii=False, indent=2)
            temp_path = Path(temp.name)
        temp_path.replace(path)
