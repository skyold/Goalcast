from pathlib import Path
from typing import Dict
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    FOOTYSTATS_API_KEY: str = ""
    ODDS_API_KEY: str = ""
    OPENWEATHER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DATABASE_URL: str = ""

    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 4000
    CLAUDE_TIMEOUT: int = 120

    LEAGUE_PARAMS: Dict[str, Dict] = {
        "Premier League": {
            "home_advantage_xg": 0.25,
            "avg_goals": 2.75,
            "low_score_bias": "medium",
        },
        "La Liga": {
            "home_advantage_xg": 0.22,
            "avg_goals": 2.65,
            "low_score_bias": "high",
        },
        "Serie A": {
            "home_advantage_xg": 0.20,
            "avg_goals": 2.55,
            "low_score_bias": "high",
        },
        "Bundesliga": {
            "home_advantage_xg": 0.28,
            "avg_goals": 3.05,
            "low_score_bias": "low",
        },
        "Ligue 1": {
            "home_advantage_xg": 0.26,
            "avg_goals": 2.60,
            "low_score_bias": "medium",
        },
        "Champions League": {
            "home_advantage_xg": 0.18,
            "avg_goals": 2.50,
            "low_score_bias": "high",
        },
    }

    HOME_ADVANTAGE_DEFAULT: float = 0.25
    AVG_GOALS_DEFAULT: float = 2.70

    CONFIDENCE_BASE: int = 70
    CONFIDENCE_MAX: int = 90
    CONFIDENCE_MIN: int = 30

    CONFIDENCE_BONUS: Dict[str, int] = {
        "market_aligned": 10,
        "lineup_confirmed": 5,
        "form_stable": 5,
    }

    CONFIDENCE_PENALTY: Dict[str, int] = {
        "no_lineup": 10,
        "severe_data_missing": 10,
        "odds_contrary": 5,
        "high_variance": 5,
        "type_c_match": 10,
        "pre_match_uncertainty": 5,
    }

    EV_THRESHOLD_RECOMMEND: float = 0.10
    EV_THRESHOLD_SMALL: float = 0.05
    EV_ADJUST_LINEUP_UNCERTAIN: float = 0.85
    EV_ADJUST_HIGH_VARIANCE: float = 0.90
    EV_ADJUST_MARKET_DEVIATION: float = 0.85

    CACHE_TTL_HOURS: Dict[str, float] = {
        "team_stats": 24.0,
        "match_data": 6.0,
        "league_table": 12.0,
        "elo": 48.0,
        "odds": 0.5,
        "weather": 3.0,
    }

    API_RATE_LIMITS: Dict[str, Dict] = {
        "footystats": {"requests_per_hour": 1800, "retry_after": 3600},
        "understat": {"min_interval_seconds": 1.5, "batch_size": 10},
        "clubelo": {"cache_hours": 48},
        "odds_api": {"free_tier_monthly": 500, "warning_threshold": 100},
        "fbref": {"min_interval_seconds": 5, "batch_size": 50},
    }

    def __init__(self):
        self.FOOTYSTATS_API_KEY = self._get_env("FOOTYSTATS_API_KEY", "")
        self.ODDS_API_KEY = self._get_env("ODDS_API_KEY", "")
        self.OPENWEATHER_API_KEY = self._get_env("OPENWEATHER_API_KEY", "")
        self.ANTHROPIC_API_KEY = self._get_env("ANTHROPIC_API_KEY", "")
        self.DATABASE_URL = self._get_env(
            "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'db' / 'goalcast.db'}"
        )

    def _get_env(self, key: str, default: str = "") -> str:
        import os
        return os.getenv(key, default)

    def get_league_params(self, league: str) -> Dict:
        return self.LEAGUE_PARAMS.get(
            league,
            {
                "home_advantage_xg": self.HOME_ADVANTAGE_DEFAULT,
                "avg_goals": self.AVG_GOALS_DEFAULT,
                "low_score_bias": "medium",
            },
        )

    def calculate_confidence(
        self,
        market_aligned: bool = False,
        lineup_confirmed: bool = False,
        form_stable: bool = False,
        no_lineup: bool = False,
        severe_data_missing: bool = False,
        odds_contrary: bool = False,
        high_variance: bool = False,
        type_c_match: bool = False,
        pre_match_uncertainty: bool = False,
    ) -> int:
        score = self.CONFIDENCE_BASE

        if market_aligned:
            score += self.CONFIDENCE_BONUS["market_aligned"]
        if lineup_confirmed:
            score += self.CONFIDENCE_BONUS["lineup_confirmed"]
        if form_stable:
            score += self.CONFIDENCE_BONUS["form_stable"]

        if no_lineup:
            score -= self.CONFIDENCE_PENALTY["no_lineup"]
        if severe_data_missing:
            score -= self.CONFIDENCE_PENALTY["severe_data_missing"]
        if odds_contrary:
            score -= self.CONFIDENCE_PENALTY["odds_contrary"]
        if high_variance:
            score -= self.CONFIDENCE_PENALTY["high_variance"]
        if type_c_match:
            score -= self.CONFIDENCE_PENALTY["type_c_match"]
        if pre_match_uncertainty:
            score -= self.CONFIDENCE_PENALTY["pre_match_uncertainty"]

        return max(self.CONFIDENCE_MIN, min(score, self.CONFIDENCE_MAX))


settings = Settings()
