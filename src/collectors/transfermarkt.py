import httpx
import asyncio
import json
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass

from src.utils.logger import logger
from src.utils.cache import cache_get, cache_set
from src.utils.rate_limiter import async_acquire
from config.settings import BASE_DIR


TM_TEAM_IDS_PATH = BASE_DIR / "config" / "tm_team_ids.json"


@dataclass
class InjuryItem:
    player_name: str
    position: str
    injury_type: str
    injury_date: str
    expected_return: str
    severity: str
    market_value: Optional[float] = None
    is_key_player: bool = False


def _load_team_ids() -> Dict[str, str]:
    if TM_TEAM_IDS_PATH.exists():
        try:
            with open(TM_TEAM_IDS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_TEAM_IDS = _load_team_ids()


class TransfermarktClient:
    BASE_URL = "https://www.transfermarkt.com"

    def __init__(self):
        self._team_ids = _TEAM_IDS
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get_team_id(self, team_name: str) -> Optional[str]:
        return self._team_ids.get(team_name)

    async def get_injuries(
        self, 
        team_name: str,
        use_cache: bool = True
    ) -> Optional[List[InjuryItem]]:
        team_id = self._get_team_id(team_name)
        if not team_id:
            logger.warning(f"Transfermarkt team ID not found for: {team_name}")
            return []

        cache_key = f"injuries:{team_id}"
        if use_cache:
            cached = cache_get("transfermarkt", cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for Transfermarkt injuries: {team_name}")
                return [InjuryItem(**item) for item in cached]

        await async_acquire("transfermarkt", 5.0)

        url = f"{self.BASE_URL}/{team_name.lower().replace(' ', '-')}/verletzte/spieler/verein/{team_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._headers)

                if response.status_code != 200:
                    logger.warning(f"Transfermarkt request failed: {response.status_code}")
                    return []

                injuries = self._parse_injuries_page(response.text, team_name)
                
                cache_set("transfermarkt", cache_key, [i.__dict__ for i in injuries], 48.0)
                return injuries

        except Exception as e:
            logger.error(f"Error fetching Transfermarkt injuries: {e}")
            return []

    async def get_suspensions(
        self,
        team_name: str,
        use_cache: bool = True
    ) -> Optional[List[InjuryItem]]:
        team_id = self._get_team_id(team_name)
        if not team_id:
            return []

        cache_key = f"suspensions:{team_id}"
        if use_cache:
            cached = cache_get("transfermarkt", cache_key)
            if cached is not None:
                return [InjuryItem(**item) for item in cached]

        await async_acquire("transfermarkt", 5.0)

        url = f"{self.BASE_URL}/{team_name.lower().replace(' ', '-')}/gesperrte/spieler/verein/{team_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._headers)

                if response.status_code != 200:
                    return []

                suspensions = self._parse_suspensions_page(response.text, team_name)
                
                cache_set("transfermarkt", cache_key, [s.__dict__ for s in suspensions], 48.0)
                return suspensions

        except Exception as e:
            logger.error(f"Error fetching Transfermarkt suspensions: {e}")
            return []

    def _parse_injuries_page(
        self, 
        html: str, 
        team_name: str
    ) -> List[InjuryItem]:
        injuries = []
        
        rows = re.findall(
            r'<tr[^>]*class="[^"]*"[^>]*>.*?</tr>',
            html, 
            re.DOTALL
        )

        for row in rows:
            try:
                player_name = self._extract_player_name(row)
                if not player_name:
                    continue

                position = self._extract_position(row)
                injury_type = self._extract_injury_type(row)
                injury_date = self._extract_injury_date(row)
                expected_return = self._extract_expected_return(row)
                market_value = self._extract_market_value(row)

                severity = self._classify_severity(expected_return)

                injuries.append(InjuryItem(
                    player_name=player_name,
                    position=position,
                    injury_type=injury_type,
                    injury_date=injury_date,
                    expected_return=expected_return,
                    severity=severity,
                    market_value=market_value,
                ))

            except Exception as e:
                logger.debug(f"Error parsing injury row: {e}")
                continue

        return injuries

    def _parse_suspensions_page(
        self,
        html: str,
        team_name: str
    ) -> List[InjuryItem]:
        suspensions = []
        
        rows = re.findall(
            r'<tr[^>]*class="[^"]*"[^>]*>.*?</tr>',
            html,
            re.DOTALL
        )

        for row in rows:
            try:
                player_name = self._extract_player_name(row)
                if not player_name:
                    continue

                position = self._extract_position(row)
                reason = self._extract_suspension_reason(row)
                matches_missed = self._extract_matches_missed(row)

                suspensions.append(InjuryItem(
                    player_name=player_name,
                    position=position,
                    injury_type=reason,
                    injury_date="",
                    expected_return=f"{matches_missed} matches",
                    severity="suspension",
                ))

            except Exception as e:
                logger.debug(f"Error parsing suspension row: {e}")
                continue

        return suspensions

    def _extract_player_name(self, html: str) -> Optional[str]:
        match = re.search(r'<a[^>]*title="([^"]+)"[^>]*class="[^"]*spielprofil_tooltip[^"]*"', html)
        if match:
            return match.group(1).strip()
        return None

    def _extract_position(self, html: str) -> str:
        match = re.search(r'<td[^>]*class="[^"]*zentriert[^"]*"[^>]*>([A-Z]{2,4})</td>', html)
        if match:
            return match.group(1)
        return "Unknown"

    def _extract_injury_type(self, html: str) -> str:
        match = re.search(r'<td[^>]*class="[^"]*verletzung[^"]*"[^>]*>([^<]+)</td>', html)
        if match:
            return match.group(1).strip()
        return "Unknown"

    def _extract_injury_date(self, html: str) -> str:
        match = re.search(r'(\d{2}/\d{2}/\d{4})', html)
        if match:
            return match.group(1)
        return ""

    def _extract_expected_return(self, html: str) -> str:
        match = re.search(r'<td[^>]*class="[^"]*hinweis[^"]*"[^>]*>([^<]+)</td>', html)
        if match:
            return match.group(1).strip()
        return "Unknown"

    def _extract_market_value(self, html: str) -> Optional[float]:
        match = re.search(r'€([0-9.]+)\s*m', html)
        if match:
            try:
                return float(match.group(1).replace('.', ''))
            except ValueError:
                pass
        return None

    def _extract_suspension_reason(self, html: str) -> str:
        match = re.search(r'<td[^>]*class="[^"]*sperre[^"]*"[^>]*>([^<]+)</td>', html)
        if match:
            return match.group(1).strip()
        return "Suspension"

    def _extract_matches_missed(self, html: str) -> int:
        match = re.search(r'(\d+)\s*match', html, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0

    def _classify_severity(self, expected_return: str) -> str:
        if not expected_return or expected_return.lower() == "unknown":
            return "unknown"
        
        expected_lower = expected_return.lower()
        
        if any(kw in expected_lower for kw in ["out for season", "long-term", "months"]):
            return "long_term"
        elif any(kw in expected_lower for kw in ["weeks", "week"]):
            return "medium_term"
        elif any(kw in expected_lower for kw in ["days", "day", "doubtful"]):
            return "short_term"
        else:
            return "unknown"


def classify_player_importance(
    injuries: List[InjuryItem],
    team_market_value_rank: Optional[Dict[str, int]] = None
) -> List[InjuryItem]:
    for injury in injuries:
        if injury.market_value is not None and team_market_value_rank:
            rank = team_market_value_rank.get(injury.player_name, 999)
            if rank <= 3:
                injury.is_key_player = True
        elif injury.position in ["GK", "CB", "ST", "CF"]:
            injury.is_key_player = True
    
    return injuries


def compute_xg_adjustment(injuries: List[InjuryItem]) -> float:
    adjustment = 0.0
    
    for injury in injuries:
        if injury.severity == "long_term":
            if injury.is_key_player:
                adjustment -= 0.30
            else:
                adjustment -= 0.15
        elif injury.severity == "medium_term":
            if injury.is_key_player:
                adjustment -= 0.20
            else:
                adjustment -= 0.10
        elif injury.severity == "short_term":
            if injury.is_key_player:
                adjustment -= 0.10
            else:
                adjustment -= 0.05
        elif injury.severity == "suspension":
            if injury.is_key_player:
                adjustment -= 0.15
            else:
                adjustment -= 0.05
    
    return round(max(adjustment, -0.50), 2)
