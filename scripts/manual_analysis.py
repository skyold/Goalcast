#!/usr/bin/env python3

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aggregator.schema import (
    AnalysisInput,
    MatchInfo,
    TeamStats,
    OddsData,
    ContextData,
    WeatherData,
    DataQuality,
    MatchType,
    DataQualityLevel,
)
from src.engine.prompt import PromptBuilder
from src.engine.runner import AnalysisRunner
from src.engine.parser import OutputParser
from src.utils.formatter import OutputFormatter
from src.utils.logger import logger


def create_manual_input(
    home_team: str,
    away_team: str,
    competition: str,
    home_xg: float = 1.5,
    away_xg: float = 1.3,
    home_xga: float = 1.0,
    away_xga: float = 1.2,
    home_elo: float = 1700,
    away_elo: float = 1650,
    home_position: int = 5,
    away_position: int = 8,
    home_form: str = "WWDWL",
    away_form: str = "WLWDL",
    odds_home: float = 2.10,
    odds_draw: float = 3.40,
    odds_away: float = 3.80,
    home_injuries: str = "",
    away_injuries: str = "",
) -> AnalysisInput:
    
    home_form_list = list(home_form) if home_form else []
    away_form_list = list(away_form) if away_form else []
    
    home_injuries_list = [i.strip() for i in home_injuries.split(",") if i.strip()]
    away_injuries_list = [i.strip() for i in away_injuries.split(",") if i.strip()]

    match_info = MatchInfo(
        match_id=f"manual_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        match_type=MatchType.A,
        data_quality=DataQualityLevel.MEDIUM,
        missing_data=["live_data"],
    )

    home_stats = TeamStats(
        team_name=home_team,
        xg_home=home_xg,
        xg_away=home_xg * 0.85,
        xga_home=home_xga,
        xga_away=home_xga * 1.1,
        ppg=2.0,
        recent_form=home_form_list,
        elo=home_elo,
        league_position=home_position,
        injuries=home_injuries_list,
    )

    away_stats = TeamStats(
        team_name=away_team,
        xg_home=away_xg * 1.1,
        xg_away=away_xg,
        xga_home=away_xga * 0.9,
        xga_away=away_xga,
        ppg=1.6,
        recent_form=away_form_list,
        elo=away_elo,
        league_position=away_position,
        injuries=away_injuries_list,
    )

    odds = OddsData(
        current_home=odds_home,
        current_draw=odds_draw,
        current_away=odds_away,
    )

    context = ContextData(
        injuries_home=home_injuries_list,
        injuries_away=away_injuries_list,
    )

    data_quality = DataQuality(
        missing_fields=["live_data"],
        quality_level=DataQualityLevel.MEDIUM,
        confidence_penalty=5,
    )

    return AnalysisInput(
        match_info=match_info,
        home_stats=home_stats,
        away_stats=away_stats,
        odds=odds,
        context=context,
        data_quality=data_quality,
    )


async def analyze_manual(
    home_team: str,
    away_team: str,
    competition: str,
    **kwargs
):
    print("\n" + "=" * 60)
    print("⚽ GOALCAST AI - 手动输入分析")
    print("=" * 60)

    print(f"\n📋 比赛: {home_team} vs {away_team}")
    print(f"📋 联赛: {competition}")

    print("\n📋 构建分析输入...")
    analysis_input = create_manual_input(
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        **kwargs
    )

    print("\n📋 构建提示词...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)
    print(f"   ✅ 提示词长度: {len(prompt)} 字符")

    print("\n📋 调用 LLM API...")
    runner = AnalysisRunner()
    
    try:
        response = await runner.run(prompt)
        if not response:
            print("   ❌ API 调用失败")
            return None
        print(f"   ✅ 响应长度: {len(response)} 字符")
    except Exception as e:
        print(f"   ❌ API 错误: {e}")
        return None

    print("\n📋 解析输出...")
    parser = OutputParser()
    output = parser.parse(response)
    
    if not output:
        print("   ❌ 解析失败")
        return None

    output_dict = output.model_dump()
    formatted = OutputFormatter.format_terminal(output_dict)
    print(formatted)

    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{home_team}_{away_team}".replace(" ", "_")
    output_file = output_dir / f"{safe_name}_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 结果已保存: {output_file}")

    return output


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Manual match analysis")
    parser.add_argument("--home", required=True, help="Home team name")
    parser.add_argument("--away", required=True, help="Away team name")
    parser.add_argument("--competition", default="Premier League", help="Competition name")
    parser.add_argument("--home-xg", type=float, default=1.5, help="Home team xG")
    parser.add_argument("--away-xg", type=float, default=1.3, help="Away team xG")
    parser.add_argument("--home-xga", type=float, default=1.0, help="Home team xGA")
    parser.add_argument("--away-xga", type=float, default=1.2, help="Away team xGA")
    parser.add_argument("--home-elo", type=float, default=1700, help="Home team Elo")
    parser.add_argument("--away-elo", type=float, default=1650, help="Away team Elo")
    parser.add_argument("--home-position", type=int, default=5, help="Home team position")
    parser.add_argument("--away-position", type=int, default=8, help="Away team position")
    parser.add_argument("--home-form", default="WWDWL", help="Home team form (e.g., WWDWL)")
    parser.add_argument("--away-form", default="WLWDL", help="Away team form")
    parser.add_argument("--odds-home", type=float, default=2.10, help="Home odds")
    parser.add_argument("--odds-draw", type=float, default=3.40, help="Draw odds")
    parser.add_argument("--odds-away", type=float, default=3.80, help="Away odds")
    parser.add_argument("--home-injuries", default="", help="Home injuries (comma separated)")
    parser.add_argument("--away-injuries", default="", help="Away injuries (comma separated)")
    
    args = parser.parse_args()
    
    kwargs = {
        "home_xg": args.home_xg,
        "away_xg": args.away_xg,
        "home_xga": args.home_xga,
        "away_xga": args.away_xga,
        "home_elo": args.home_elo,
        "away_elo": args.away_elo,
        "home_position": args.home_position,
        "away_position": args.away_position,
        "home_form": args.home_form,
        "away_form": args.away_form,
        "odds_home": args.odds_home,
        "odds_draw": args.odds_draw,
        "odds_away": args.odds_away,
        "home_injuries": args.home_injuries,
        "away_injuries": args.away_injuries,
    }
    
    asyncio.run(analyze_manual(
        home_team=args.home,
        away_team=args.away,
        competition=args.competition,
        **kwargs
    ))


if __name__ == "__main__":
    main()
