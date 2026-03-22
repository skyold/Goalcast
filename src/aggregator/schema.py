from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MatchType(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class DataQualityLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BetRating(str, Enum):
    RECOMMEND = "推荐"
    SMALL = "小注"
    NOT_RECOMMEND = "不推荐"


class SignalDirection(str, Enum):
    SUPPORT = "支持模型"
    OPPOSE = "反对模型"
    NEUTRAL = "中立"


class SignalStrength(str, Enum):
    STRONG = "强"
    MEDIUM = "中"
    WEAK = "弱"


class TeamStats(BaseModel):
    team_id: Optional[str] = None
    team_name: Optional[str] = None
    xg_home: Optional[float] = Field(None, ge=0, le=5)
    xg_away: Optional[float] = Field(None, ge=0, le=5)
    xga_home: Optional[float] = Field(None, ge=0, le=5)
    xga_away: Optional[float] = Field(None, ge=0, le=5)
    ppg: Optional[float] = Field(None, ge=0, le=4)
    possession_home: Optional[float] = Field(None, ge=0, le=100)
    possession_away: Optional[float] = Field(None, ge=0, le=100)
    recent_form: List[str] = Field(default_factory=list)
    elo: Optional[float] = Field(None, ge=0, le=3000)
    league_position: Optional[int] = Field(None, ge=1, le=30)
    zone: Optional[str] = None
    injuries: List[str] = Field(default_factory=list)
    suspensions: List[str] = Field(default_factory=list)


class MatchInfo(BaseModel):
    match_id: str
    home_team: str
    away_team: str
    competition: str
    match_type: MatchType = MatchType.A
    kickoff_dt: Optional[datetime] = None
    first_leg_score: Optional[str] = None
    data_quality: DataQualityLevel = DataQualityLevel.MEDIUM
    missing_data: List[str] = Field(default_factory=list)


class OddsData(BaseModel):
    opening_home: Optional[float] = Field(None, ge=1.0)
    opening_draw: Optional[float] = Field(None, ge=1.0)
    opening_away: Optional[float] = Field(None, ge=1.0)
    current_home: Optional[float] = Field(None, ge=1.0)
    current_draw: Optional[float] = Field(None, ge=1.0)
    current_away: Optional[float] = Field(None, ge=1.0)
    implied_home: Optional[float] = Field(None, ge=0, le=1)
    implied_draw: Optional[float] = Field(None, ge=0, le=1)
    implied_away: Optional[float] = Field(None, ge=0, le=1)
    movement_home: Optional[float] = None
    movement_draw: Optional[float] = None
    movement_away: Optional[float] = None

    @field_validator("implied_home", "implied_draw", "implied_away", mode="before")
    @classmethod
    def validate_implied(cls, v):
        if v is not None:
            return max(0.0, min(1.0, v))
        return None


class ContextData(BaseModel):
    injuries_home: List[str] = Field(default_factory=list)
    injuries_away: List[str] = Field(default_factory=list)
    schedule_density_home: Optional[int] = None
    schedule_density_away: Optional[int] = None
    motivation_notes: Optional[str] = None
    tactical_notes: Optional[str] = None
    weather: Optional[Dict[str, Any]] = None


class WeatherData(BaseModel):
    wind_speed: float = 0
    rainfall: float = 0
    condition: str = "Unknown"
    xg_adjustment: float = 0


class DataQuality(BaseModel):
    missing_fields: List[str] = Field(default_factory=list)
    quality_level: DataQualityLevel = DataQualityLevel.MEDIUM
    confidence_penalty: int = 0


class AnalysisInput(BaseModel):
    version: str = "1.0"
    timestamp: datetime = Field(default_factory=datetime.now)
    match_info: MatchInfo
    home_stats: TeamStats
    away_stats: TeamStats
    odds: Optional[OddsData] = None
    context: ContextData = Field(default_factory=ContextData)
    weather: Optional[WeatherData] = None
    data_quality: DataQuality = Field(default_factory=DataQuality)


class ModelOutput(BaseModel):
    base_xg: Dict[str, float] = Field(default_factory=dict)
    adjusted_xg: Dict[str, float] = Field(default_factory=dict)
    final_probabilities: Dict[str, str] = Field(default_factory=dict)
    top_scores: List[Dict[str, str]] = Field(default_factory=list)


class MarketData(BaseModel):
    market_probabilities: Dict[str, str] = Field(default_factory=dict)
    divergence: Dict[str, float] = Field(default_factory=dict)
    signal_direction: SignalDirection = SignalDirection.NEUTRAL
    signal_strength: SignalStrength = SignalStrength.WEAK


class DecisionData(BaseModel):
    ev: float = 0
    risk_adjusted_ev: float = 0
    best_bet: str = ""
    bet_rating: BetRating = BetRating.NOT_RECOMMEND
    confidence: int = 50


class ReasoningChain(BaseModel):
    layer1_summary: str = ""
    layer2_adjustments: List[str] = Field(default_factory=list)
    layer3_signal: str = ""
    layer4_tempo: str = ""
    layer5_top_score_logic: str = ""
    layer6_bayesian_update: str = ""
    layer7_ev_calc: str = ""
    layer8_confidence_breakdown: str = ""


class MetaData(BaseModel):
    match_type_classification: str = ""
    league_params_used: str = ""
    data_quality_notes: str = ""


class AnalysisOutput(BaseModel):
    match_info: MatchInfo
    model_output: ModelOutput
    market: MarketData
    decision: DecisionData
    reasoning_chain: ReasoningChain
    meta: MetaData


class LeagueParams(BaseModel):
    home_advantage_xg: float = 0.25
    avg_goals: float = 2.70
    low_score_bias: str = "medium"
