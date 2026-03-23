from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from src.aggregator.schema import AnalysisInput, MatchType
from utils.logger import logger


PROMPT_VERSION = "v3.0"
PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / f"{PROMPT_VERSION}.md"


LEAGUE_PARAMS_TEMPLATE = """
## 联赛参数

| 联赛 | 主场优势 xG | 场均进球 | 低比分偏差 |
|------|------------|----------|------------|
| 英超 | +0.25 | 2.75 | 中等 |
| 西甲 | +0.22 | 2.65 | 较高 |
| 意甲 | +0.20 | 2.55 | 高 |
| 德甲 | +0.28 | 3.05 | 低 |
| 法甲 | +0.26 | 2.60 | 中等 |
| 欧冠 | +0.18 | 2.50 | 高 |
"""


MATCH_TYPE_TEMPLATE = """
## 比赛类型分类

| 类型 | 描述 | 特殊建模逻辑 |
|------|------|--------------|
| A | 联赛常规轮次 | 标准双方动力分析，均值回归正常权重 |
| B | 杯赛单场淘汰 | 防守概率上调，低比分/加时/点球建模，进球方差 +15% |
| C | 双回合次回合 | 输入首回合比分，进球需求建模，战略意图权重提升 |
| D | 关键联赛（积分攸关） | 动力调整系数 ×1.5 |
"""


DATA_QUALITY_TEMPLATE = """
## 数据质量说明

{data_missing_text}

数据降级规则：
- FotMob 阵容不可用：第二层调整幅度上限压缩至 ±0.2 xG，置信度 -10
- 仅有开盘赔率，无即时赔率：第三层权重自动降至 5%，标注"低可信度"
- 统计数据不可用：标注"基于估算"，data_quality = low
- 禁止编造任何统计数字
"""


class PromptBuilder:
    def __init__(self, prompt_file: Optional[Path] = None):
        self.prompt_file = prompt_file or PROMPT_FILE
        self.version = PROMPT_VERSION

    def build(self, input_data: AnalysisInput) -> str:
        logger.info("Building prompt from analysis input")

        match_info = input_data.match_info
        home = input_data.home_stats
        away = input_data.away_stats

        prompt_parts = []

        prompt_parts.append(self._build_header())
        prompt_parts.append(self._build_match_info(match_info))
        prompt_parts.append(self._build_team_data("主队", home, is_home=True))
        prompt_parts.append(self._build_team_data("客队", away, is_home=False))
        prompt_parts.append(self._build_market_data(input_data.odds))
        prompt_parts.append(self._build_context_data(input_data))
        prompt_parts.append(self._build_weather_data(input_data.weather))
        prompt_parts.append(LEAGUE_PARAMS_TEMPLATE)
        prompt_parts.append(self._build_match_type_section(match_info.match_type))
        prompt_parts.append(self._build_data_quality_section(input_data.data_quality.missing_fields))
        prompt_parts.append(self._build_output_format())
        prompt_parts.append(self._build_analysis_instructions())

        return "\n\n".join(prompt_parts)

    def _build_header(self) -> str:
        return f"""# Goalcast AI — Football Prediction Analysis
Version: {self.version}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

你是一个专业的足球比赛分析师，基于量化模型和概率论进行比赛预测。
核心原则：
- 不编造统计数字，数据不可得时必须显式降权而非估算填充
- 置信度上限 90 分，禁止输出"必赢"结论
- 每场分析必须完整执行零层数据检查
- 投注建议仅在 EV > 0.05 时输出
"""

    def _build_match_info(self, match_info) -> str:
        parts = [
            "## 比赛信息",
            f"- **match_id**: {match_info.match_id}",
            f"- **主队**: {match_info.home_team}",
            f"- **客队**: {match_info.away_team}",
            f"- **联赛**: {match_info.competition}",
            f"- **比赛类型**: {match_info.match_type.value} ({self._match_type_description(match_info.match_type)})",
        ]

        if match_info.first_leg_score:
            parts.append(f"- **首回合比分**: {match_info.first_leg_score}")

        return "\n".join(parts)

    def _match_type_description(self, match_type: MatchType) -> str:
        descriptions = {
            MatchType.A: "联赛常规轮次",
            MatchType.B: "杯赛单场淘汰",
            MatchType.C: "双回合次回合",
            MatchType.D: "关键联赛（积分攸关）",
        }
        return descriptions.get(match_type, "联赛常规轮次")

    def _build_team_data(self, team_label: str, stats, is_home: bool) -> str:
        parts = [
            f"## {team_label}数据 ({stats.team_name or 'Unknown'})",
        ]

        xg = stats.xg_home if is_home else stats.xg_away
        xga = stats.xga_home if is_home else stats.xga_away

        if xg is not None:
            parts.append(f"- **赛季xG**: {xg:.2f}")
        else:
            parts.append("- **赛季xG**: 数据不可用")

        if xga is not None:
            parts.append(f"- **赛季xGA**: {xga:.2f}")
        else:
            parts.append("- **赛季xGA**: 数据不可用")

        if stats.ppg:
            parts.append(f"- **场均积分**: {stats.ppg:.2f}")

        if stats.recent_form:
            form_str = " ".join(stats.recent_form[-5:])
            parts.append(f"- **近期5场**: {form_str}")

        if stats.elo:
            parts.append(f"- **Elo评分**: {stats.elo:.0f}")

        if stats.league_position:
            parts.append(f"- **联赛排名**: 第{stats.league_position}位")

        if stats.zone:
            parts.append(f"- **区域**: {stats.zone}")

        if stats.injuries:
            parts.append(f"- **伤病**: {', '.join(stats.injuries)}")

        return "\n".join(parts)

    def _build_market_data(self, odds) -> str:
        if not odds:
            return "## 市场赔率\n- **状态**: 数据不可用"

        parts = [
            "## 市场赔率",
        ]

        if odds.opening_home:
            parts.append(f"- **开盘赔率**: 主 {odds.opening_home:.2f} | 平 {odds.opening_draw:.2f} | 客 {odds.opening_away:.2f}")

        if odds.current_home:
            parts.append(f"- **即时赔率**: 主 {odds.current_home:.2f} | 平 {odds.current_draw:.2f} | 客 {odds.current_away:.2f}")

        if odds.implied_home:
            parts.append(f"- **市场隐含概率**: 主 {odds.implied_home:.1%} | 平 {odds.implied_draw:.1%} | 客 {odds.implied_away:.1%}")

        if odds.movement_home:
            parts.append(f"- **赔率变动**: 主 {odds.movement_home:+.2f} | 平 {odds.movement_draw:+.2f} | 客 {odds.movement_away:+.2f}")

        return "\n".join(parts)

    def _build_context_data(self, input_data: AnalysisInput) -> str:
        context = input_data.context
        parts = ["## 情境数据"]

        if context.injuries_home:
            parts.append(f"- **主队伤病**: {', '.join(context.injuries_home)}")
        if context.injuries_away:
            parts.append(f"- **客队伤病**: {', '.join(context.injuries_away)}")

        if context.schedule_density_home:
            parts.append(f"- **主队7天内赛程**: {context.schedule_density_home}场")
        if context.schedule_density_away:
            parts.append(f"- **客队7天内赛程**: {context.schedule_density_away}场")

        if context.motivation_notes:
            parts.append(f"- **动力因素**: {context.motivation_notes}")

        if context.tactical_notes:
            parts.append(f"- **战术笔记**: {context.tactical_notes}")

        return "\n".join(parts)

    def _build_weather_data(self, weather) -> str:
        if not weather:
            return "## 天气数据\n- **状态**: 数据不可用（无影响）"

        parts = [
            "## 天气数据",
            f"- **条件**: {weather.condition}",
            f"- **风速**: {weather.wind_speed} m/s",
            f"- **降水**: {weather.rainfall} mm",
            f"- **xG调整**: {weather.xg_adjustment:+.2f}",
        ]

        return "\n".join(parts)

    def _build_match_type_section(self, match_type: MatchType) -> str:
        return MATCH_TYPE_TEMPLATE

    def _build_data_quality_section(self, missing_fields: list) -> str:
        if not missing_fields:
            data_text = "- **数据状态**: 完整，所有核心数据可用"
        else:
            data_text = f"- **缺失数据**: {', '.join(missing_fields)}\n- 系统将自动应用降级规则"

        return DATA_QUALITY_TEMPLATE.format(data_missing_text=data_text)

    def _build_output_format(self) -> str:
        return """
## 输出格式要求

请以JSON格式输出完整的分析结果：

```json
{
  "match_info": {
    "home_team": "",
    "away_team": "",
    "competition": "",
    "match_type": "A|B|C|D",
    "data_quality": "high|medium|low",
    "missing_data": []
  },
  "model_output": {
    "base_xg": { "home": 0.0, "away": 0.0 },
    "adjusted_xg": { "home": 0.0, "away": 0.0 },
    "final_probabilities": {
      "home_win": "0%",
      "draw": "0%",
      "away_win": "0%"
    },
    "top_scores": [
      { "score": "1-0", "probability": "0%" },
      { "score": "1-1", "probability": "0%" }
    ]
  },
  "market": {
    "market_probabilities": { "home_win": "0%", "draw": "0%", "away_win": "0%" },
    "divergence": { "home_win": 0.0, "draw": 0.0, "away_win": 0.0 },
    "signal_direction": "支持模型|反对模型|中立",
    "signal_strength": "强|中|弱"
  },
  "decision": {
    "ev": 0.0,
    "risk_adjusted_ev": 0.0,
    "best_bet": "",
    "bet_rating": "推荐|小注|不推荐",
    "confidence": 0
  },
  "reasoning_chain": {
    "layer1_summary": "",
    "layer2_adjustments": [],
    "layer3_signal": "",
    "layer4_tempo": "",
    "layer5_top_score_logic": "",
    "layer6_bayesian_update": "跳过|[更新内容]",
    "layer7_ev_calc": "",
    "layer8_confidence_breakdown": ""
  },
  "meta": {
    "match_type_classification": "",
    "league_params_used": "",
    "data_quality_notes": ""
  }
}
```

**重要**：
- 概率三项之和必须等于100%（允许±0.5%误差）
- 置信度必须在[30, 90]范围内
- EV值必须在[-1, +2]范围内
- reasoning_chain各字段必须非空
"""

    def _build_analysis_instructions(self) -> str:
        return """
---

## 分析任务

请按以下8层框架进行完整分析：

### 零层：赛前强制检查
检查所有必要数据是否可用，识别缺失数据并应用降级规则。

### 第一层：基础实力模型（权重35%）
- 计算均值回归xG：赛季xG × 0.7 + 近5场xG × 0.3
- 应用主场优势调整
- 计算Elo胜率概率

### 第二层：情境调整模型（权重20%）
根据伤病、疲劳、动力、战术变化调整xG预测。

### 第三层：市场行为分析（权重20%）
- 比较模型概率与市场隐含概率
- 识别市场与模型的背离
- 判断精明资金方向

### 第四层：节奏方差模型（权重5%）
- 分析PPDA、控球率
- 判断开放型/封闭型比赛

### 第五层：分布模型（权重10%）
使用Dixon-Coles修正泊松分布生成比分矩阵。

### 第六层：贝叶斯更新（权重5%）
仅在阵容变化或赔率剧变时触发更新。

### 第七层：EV与Kelly决策
- EV = (模型概率 × 赔率) - 1
- 应用风险调整系数
- 输出投注建议

### 第八层：置信度校准
根据数据质量和分析确定性输出置信度评分。

**请开始分析并输出JSON格式结果。**
"""
