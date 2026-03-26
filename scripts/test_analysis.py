#!/usr/bin/env python3

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from aggregator.schema import (
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
from engine.prompt import PromptBuilder
from engine.runner import AnalysisRunner
from engine.parser import OutputParser
from utils.logger import logger


def create_mock_analysis_input() -> AnalysisInput:
    match_info = MatchInfo(
        match_id="mock_001",
        home_team="Arsenal",
        away_team="Chelsea",
        competition="Premier League",
        match_type=MatchType.A,
        data_quality=DataQualityLevel.HIGH,
        missing_data=[],
    )

    home_stats = TeamStats(
        team_id="1",
        team_name="Arsenal",
        xg_home=1.85,
        xg_away=1.45,
        xga_home=0.95,
        xga_away=1.15,
        ppg=2.15,
        possession_home=58.5,
        possession_away=52.3,
        recent_form=["W", "W", "D", "W", "L"],
        elo=1785.0,
        league_position=2,
        injuries=["Tierney (out)"],
    )

    away_stats = TeamStats(
        team_id="2",
        team_name="Chelsea",
        xg_home=1.72,
        xg_away=1.38,
        xga_home=1.05,
        xga_away=1.22,
        ppg=1.85,
        possession_home=55.2,
        possession_away=48.7,
        recent_form=["W", "L", "W", "D", "W"],
        elo=1720.0,
        league_position=6,
        injuries=["James (doubtful)"],
    )

    odds = OddsData(
        opening_home=2.10,
        opening_draw=3.50,
        opening_away=3.80,
        current_home=2.05,
        current_draw=3.40,
        current_away=3.90,
        implied_home=0.476,
        implied_draw=0.286,
        implied_away=0.256,
    )

    context = ContextData(
        injuries_home=["Tierney (out)"],
        injuries_away=["James (doubtful)"],
        schedule_density_home=2,
        schedule_density_away=3,
        motivation_notes="Top 4 clash - high motivation for both sides",
    )

    weather = WeatherData(
        wind_speed=5.2,
        rainfall=0.0,
        condition="Clear",
        xg_adjustment=0.0,
    )

    data_quality = DataQuality(
        missing_fields=[],
        quality_level=DataQualityLevel.HIGH,
        confidence_penalty=0,
    )

    return AnalysisInput(
        match_info=match_info,
        home_stats=home_stats,
        away_stats=away_stats,
        odds=odds,
        context=context,
        weather=weather,
        data_quality=data_quality,
    )


async def test_analysis_flow():
    print("\n" + "=" * 60)
    print("🧪 GOALCAST AI - 测试分析流程")
    print("=" * 60)

    print("\n📋 步骤 1: 创建模拟输入数据...")
    analysis_input = create_mock_analysis_input()
    print(f"   ✅ 比赛: {analysis_input.match_info.home_team} vs {analysis_input.match_info.away_team}")
    print(f"   ✅ 联赛: {analysis_input.match_info.competition}")
    print(f"   ✅ 数据质量: {analysis_input.match_info.data_quality.value}")

    print("\n📋 步骤 2: 构建提示词...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)
    print(f"   ✅ 提示词长度: {len(prompt)} 字符")

    print("\n📋 步骤 3: 调用 LLM API...")
    runner = AnalysisRunner()
    
    try:
        response = await runner.run(prompt)
        if response:
            print(f"   ✅ 响应长度: {len(response)} 字符")
        else:
            print("   ❌ API 调用失败")
            return None
    except Exception as e:
        print(f"   ❌ API 错误: {e}")
        return None

    print("\n📋 步骤 4: 解析输出...")
    parser = OutputParser()
    output = parser.parse(response)
    
    if output:
        print("   ✅ 解析成功")
        output_dict = output.model_dump()
    else:
        print("   ❌ 解析失败")
        output_dict = {"error": "Parsing failed", "raw_response": response[:500]}

    print("\n📋 步骤 5: 格式化输出...")
    formatted = OutputFormatter.format_terminal(output_dict)
    print(formatted)

    output_dir = Path("data/exports")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"test_analysis_{timestamp}.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n💾 结果已保存: {output_file}")

    return output


async def test_dry_run():
    print("\n" + "=" * 60)
    print("🧪 GOALCAST AI - Dry Run 测试 (不调用API)")
    print("=" * 60)

    print("\n📋 创建模拟输入数据...")
    analysis_input = create_mock_analysis_input()
    
    print("\n📋 构建提示词...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)
    
    print("\n" + "-" * 60)
    print("📝 生成的提示词预览 (前2000字符):")
    print("-" * 60)
    print(prompt[:2000])
    print("\n... [截断] ...")
    print(f"\n提示词总长度: {len(prompt)} 字符")

    print("\n📋 输入数据 JSON:")
    input_dict = analysis_input.model_dump()
    print(json.dumps(input_dict, indent=2, ensure_ascii=False, default=str))

    return prompt


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Test Goalcast AI analysis flow")
    parser.add_argument("--dry-run", action="store_true", help="Only build prompt, don't call API")
    args = parser.parse_args()

    if args.dry_run:
        asyncio.run(test_dry_run())
    else:
        asyncio.run(test_analysis_flow())


if __name__ == "__main__":
    main()
