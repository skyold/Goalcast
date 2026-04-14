"""
数据策略层 — 数据模型

定义分析层唯一依赖的数据契约：MatchContext。
所有 Skill 只消费 MatchContext，不直接调用 provider MCP 工具。

设计原则：
- 不可变（frozen dataclass / tuple 替代 list）
- 字段语义清晰，附带来源与质量元数据
- data_gaps 显式标记缺失项，而非静默忽略
"""

from dataclasses import dataclass
from typing import Optional, Tuple


# ── 联赛常量 ────────────────────────────────────────────────

# Understat 覆盖的联赛（内部代码 → Understat API 代码）
UNDERSTAT_LEAGUE_MAP: dict[str, str] = {
    # FootyStats / 用户输入可能的名称 → Understat 代码
    "Premier League": "EPL",
    "England Premier League": "EPL",
    "EPL": "EPL",
    "La Liga": "La_Liga",
    "Spanish La Liga": "La_Liga",
    "La_liga": "La_Liga",
    "La_Liga": "La_Liga",
    "Bundesliga": "Bundesliga",
    "German Bundesliga": "Bundesliga",
    "Serie A": "Serie_A",
    "Italian Serie A": "Serie_A",
    "Serie_A": "Serie_A",
    "Ligue 1": "Ligue_1",
    "French Ligue 1": "Ligue_1",
    "Ligue_1": "Ligue_1",
    "RFPL": "RFPL",
    "Russian Premier League": "RFPL",
}

UNDERSTAT_SUPPORTED_LEAGUES: frozenset[str] = frozenset(UNDERSTAT_LEAGUE_MAP.keys())


def get_understat_league_code(league_name: str) -> Optional[str]:
    """将联赛名映射为 Understat API 代码；不支持的联赛返回 None。"""
    return UNDERSTAT_LEAGUE_MAP.get(league_name)


# ── 子数据类型（frozen，值对象）───────────────────────────────


@dataclass(frozen=True)
class TeamFormWindow:
    """
    球队在特定场次窗口（5 场 / 10 场）内的表现统计。
    来源：FootyStats get_team_last_x_stats
    """

    games: int                    # 窗口场次数（5 或 10）
    wins: int
    draws: int
    losses: int
    goals_scored: float           # 总进球
    goals_conceded: float         # 总失球
    avg_scored: float             # 场均进球（seasonScoredAVG_overall）
    avg_conceded: float           # 场均失球（seasonConcededAVG_overall）


@dataclass(frozen=True)
class StandingsEntry:
    """
    单支球队的积分榜状态。
    来源：FootyStats get_league_tables
    """

    position: int
    points: int
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int


@dataclass(frozen=True)
class OddsSnapshot:
    """
    赛前博彩赔率快照（十进制赔率）。
    来源：FootyStats match_details（odds_ft_1/x/2）
    """

    home_win: float              # 主胜赔率
    draw: float                  # 平局赔率
    away_win: float              # 客胜赔率
    source: str                  # "footystats" | "sportmonks"
    quality: float               # 0.0 – 1.0


@dataclass(frozen=True)
class AsianHandicapOdds:
    """
    亚盘（Asian Handicap）赔率快照。
    来源：Sportmonks prematch_odds → Asian Handicap market（主盘线）

    ah_line 含义：
      - 负值：主队让球（如 -0.5 = 主队让半球，-1.0 = 主队让一球）
      - 正值：客队让球（如 +0.5 = 主队受让半球）
      - 四分之一盘：-0.25 / -0.75（上下盘各半，仅一半注金退还）
    """
    ah_line: float               # 主队让球线（主盘线）
    ah_home_odds: float          # 主队（让球后）赔率
    ah_away_odds: float          # 客队（受让后）赔率
    source: str                  # "sportmonks_cached" | "sportmonks"
    quality: float               # 0.0 – 1.0


@dataclass(frozen=True)
class XGStats:
    """
    双方的 xG 攻防代理值（场均）。

    这是分析模型 L1 层的核心输入，对应：
    - home_xg_for  → 主队进攻强度（xG/场）
    - home_xg_against → 主队防守强度（xGA/场）
    同理适用于客队。

    source 优先级（由 resolver 保证）：
      "sportmonks_direct" > "understat_direct" > "footystats_proxy" > "league_avg"
    """

    home_xg_for: float
    home_xg_against: float
    away_xg_for: float
    away_xg_against: float
    source: str                  # 见上方优先级说明
    quality: float               # 0.0 – 1.0


@dataclass(frozen=True)
class MatchLineups:
    """
    双方阵型与首发确认状态。
    来源：Sportmonks lineups include
    """
    home_formation: Optional[str]   # "4-3-3"，未公布时为 None
    away_formation: Optional[str]
    home_confirmed: bool            # 是否已确认首发
    away_confirmed: bool


@dataclass(frozen=True)
class OddsMovement:
    """
    赔率变动快照（开盘 vs 当前）。
    来源：Sportmonks odds_movement
    """
    home_open: float
    home_current: float
    draw_open: float
    draw_current: float
    away_open: float
    away_current: float
    movement_hours: int             # 赔率变动时间跨度（小时）


@dataclass(frozen=True)
class H2HEntry:
    """
    单场历史交锋记录。
    来源：Sportmonks head_to_head
    """
    date: str                       # YYYY-MM-DD
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class PredictionSnapshot:
    """
    Sportmonks 预测概率快照。
    来源：Sportmonks predictions/probabilities
    """
    home_win: float              # 主胜概率 (0.0 - 1.0)
    draw: float                  # 平局概率 (0.0 - 1.0)
    away_win: float              # 客胜概率 (0.0 - 1.0)
    source: str                  # "sportmonks"
    quality: float               # 0.0 - 1.0


# ── 主契约对象 ────────────────────────────────────────────────


@dataclass
class MatchContext:
    """
    单场比赛的完整数据上下文。

    由 DataFusion 构建，是 Skill 分析层的唯一数据输入。
    Skill 不直接调用任何 provider MCP 工具，只读取此对象。

    字段分组：
      - 比赛标识：match_id / team_id / league 等
      - L1 xG 数据：xg（可为 None，查看 data_gaps）
      - L1 近况数据：home_form_5 / home_form_10 等
      - L1 积分榜：home_standing / away_standing
      - L3 赔率：odds
      - 元数据：data_gaps / overall_quality / sources / resolved_at
    """

    # ── 新增：provider 标识（最重要，放首位）─────────────────
    data_provider: str               # "sportmonks" | "footystats"

    # ── 比赛标识（原有，不变）─────────────────────────────────
    match_id: str                # FootyStats match ID
    league: str                  # 联赛名（如 "Premier League"）
    home_team: str
    home_team_id: str
    away_team: str
    away_team_id: str
    season_id: str               # FootyStats competition/season ID
    match_date: Optional[str]    # YYYY-MM-DD

    # ── L1：xG 攻防数据 ───────────────────────────────────
    xg: Optional[XGStats]        # None → 见 data_gaps

    # ── L1：近况数据 ──────────────────────────────────────
    home_form_5: Optional[TeamFormWindow]
    home_form_10: Optional[TeamFormWindow]
    away_form_5: Optional[TeamFormWindow]
    away_form_10: Optional[TeamFormWindow]
    form_source: str             # "footystats" | "missing"
    form_quality: float          # 0.0 – 1.0

    # ── L1：积分榜 ────────────────────────────────────────
    home_standing: Optional[StandingsEntry]
    away_standing: Optional[StandingsEntry]
    total_teams: int             # 联赛球队总数（用于百分位计算）
    standings_source: str        # "footystats" | "missing"
    standings_quality: float     # 0.0 – 1.0

    # ── L3：赔率 ──────────────────────────────────────────
    odds: Optional[OddsSnapshot] # None → 见 data_gaps

    # ── Layer AH：亚盘赔率快照 ────────────────────────────
    asian_handicap: Optional["AsianHandicapOdds"]  # None → AH 数据缺失，见 data_gaps

    # ── 新增：Sportmonks 独有字段──────────────────────────────
    lineups: Optional[MatchLineups]
    odds_movement: Optional[OddsMovement]
    head_to_head: Optional[tuple]    # tuple[H2HEntry, ...] or None
    predictions: Optional[PredictionSnapshot] # 官方胜平负预测概率

    # ── 元数据 ────────────────────────────────────────────
    data_gaps: tuple             # 缺失数据项列表，如 ("lineups", "injuries")
    overall_quality: float       # 0.0 – 1.0，综合数据质量评分
    sources: dict                # {"xg": "understat_direct", "odds": "footystats"}
    resolved_at: float           # Unix 时间戳

    def to_dict(self) -> dict:
        """序列化为可 JSON 化的字典（供 MCP 工具返回）。"""
        from dataclasses import asdict
        import math

        def _clean(obj):
            """递归清理：tuple → list，nan → None。"""
            if isinstance(obj, dict):
                return {k: _clean(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_clean(i) for i in obj]
            if isinstance(obj, float) and math.isnan(obj):
                return None
            return obj

        return _clean(asdict(self))
