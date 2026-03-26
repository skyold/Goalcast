import re
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from provider.base import BaseProvider
from utils.logger import logger
from config.settings import BASE_DIR


TM_TEAM_IDS_PATH = BASE_DIR / "config" / "tm_team_ids.json"


def _load_team_ids() -> Dict[str, str]:
    if TM_TEAM_IDS_PATH.exists():
        try:
            with open(TM_TEAM_IDS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_TEAM_IDS = _load_team_ids()


class TransfermarktProvider(BaseProvider):
    BASE_URL = "https://www.transfermarkt.com"
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = None):
        super().__init__("", timeout)
        self._team_ids = _TEAM_IDS

    @property
    def name(self) -> str:
        return "transfermarkt"

    async def is_available(self) -> bool:
        return True

    def _get_team_id(self, team_name: str) -> Optional[str]:
        return self._team_ids.get(team_name)

    def _get_team_slug(self, team_name: str) -> str:
        return team_name.lower().replace(" ", "-").replace(".", "")

    async def get_injuries(self, team_name: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_injuries({team_name})")
        
        team_id = self._get_team_id(team_name)
        team_slug = self._get_team_slug(team_name)
        
        if team_id:
            url = f"/{team_slug}/verletzungen/spielerverein/{team_id}"
        else:
            url = f"/{team_slug}/verletzungen/spielerverein"
        
        response = await self._request(url)
        if response:
            return {"html": response, "team_name": team_name}
        
        return None

    async def get_suspensions(self, team_name: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_suspensions({team_name})")
        
        team_id = self._get_team_id(team_name)
        team_slug = self._get_team_slug(team_name)
        
        if team_id:
            url = f"/{team_slug}/sperren/spielerverein/{team_id}"
        else:
            url = f"/{team_slug}/sperren/spielerverein"
        
        response = await self._request(url)
        if response:
            return {"html": response, "team_name": team_name}
        
        return None

    async def get_squad(self, team_name: str) -> Optional[Dict[str, Any]]:
        logger.debug(f"Provider {self.name}: get_squad({team_name})")
        
        team_id = self._get_team_id(team_name)
        team_slug = self._get_team_slug(team_name)
        
        if team_id:
            url = f"/{team_slug}/kader/spielerverein/{team_id}"
        else:
            url = f"/{team_slug}/kader/spielerverein"
        
        response = await self._request(url)
        if response:
            return {"html": response, "team_name": team_name}
        
        return None

    def parse_injury_html(self, html_content: str, team_name: str) -> List[Dict[str, Any]]:
        injuries = []
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            rows = soup.select("table.items tbody tr")
            
            for row in rows:
                try:
                    player_cell = row.select_one("td.hauptlink a")
                    if not player_cell:
                        continue
                    
                    player_name = player_cell.get_text(strip=True)
                    
                    position_cell = row.select_one("td.posrela")
                    position = ""
                    if position_cell:
                        pos_span = position_cell.select_one("span")
                        if pos_span:
                            position = pos_span.get_text(strip=True)
                    
                    cells = row.select("td")
                    injury_type = ""
                    injury_date = ""
                    expected_return = ""
                    
                    if len(cells) >= 4:
                        injury_type = cells[2].get_text(strip=True)
                        injury_date = cells[3].get_text(strip=True)
                    if len(cells) >= 5:
                        expected_return = cells[4].get_text(strip=True)
                    
                    severity = self._classify_severity(expected_return)
                    
                    injuries.append({
                        "player_name": player_name,
                        "team_name": team_name,
                        "position": position,
                        "injury_type": injury_type,
                        "injury_date": injury_date,
                        "expected_return": expected_return,
                        "severity": severity,
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing injury row: {e}")
                    continue
                    
        except ImportError:
            logger.warning("BeautifulSoup not installed. Install with: pip install beautifulsoup4")
        except Exception as e:
            logger.error(f"Error parsing injury HTML: {e}")
        
        return injuries

    def _classify_severity(self, expected_return: str) -> str:
        expected_lower = expected_return.lower()
        
        if any(x in expected_lower for x in ["out for season", "long-term", "months", "season"]):
            return "long_term"
        elif any(x in expected_lower for x in ["weeks", "week"]):
            return "medium_term"
        elif any(x in expected_lower for x in ["days", "day", "doubtful"]):
            return "short_term"
        elif "suspension" in expected_lower or "suspended" in expected_lower:
            return "suspension"
        else:
            return "unknown"

    def __repr__(self) -> str:
        return f"<TransfermarktProvider>"
