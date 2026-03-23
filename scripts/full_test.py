#!/usr/bin/env python3

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.football_data import FootballDataClient
from src.aggregator.schema import (
    AnalysisInput,
    MatchInfo,
    TeamStats,
    OddsData,
    ContextData,
    DataQuality,
    MatchType,
    DataQualityLevel,
)
from src.engine.prompt import PromptBuilder
from src.engine.runner import AnalysisRunner
from src.engine.parser import OutputParser
from src.utils.formatter import OutputFormatter
from src.utils.logger import logger
from config.settings import settings


async def get_upcoming_matches():
    print("\n" + "=" * 60)
    print("📋 获取未来比赛")
    print("=" * 60)
    
    client = FootballDataClient()
    
    today = datetime.now()
    date_from = today.strftime("%Y-%m-%d")
    date_to = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    
    matches = await client.get_matches("Premier League", date_from, date_to)
    
    if not matches:
        print("❌ 未获取到比赛数据")
        return None
    
    upcoming = [m for m in matches if m.get("status") == "SCHEDULED" or m.get("utc_date", "") >= today.isoformat()]
    
    print(f"\n✅ 找到 {len(upcoming)} 场即将进行的比赛:\n")
    
    for i, m in enumerate(upcoming[:10], 1):
        date_str = m.get("utc_date", "")[:10] if m.get("utc_date") else "未知日期"
        print(f"   {i}. {m['home_name']} vs {m['away_name']} ({date_str})")
    
    return upcoming


async def analyze_match_with_football_data(match_data: dict):
    print("\n" + "=" * 60)
    print("⚽ 开始分析比赛")
    print("=" * 60)
    
    client = FootballDataClient()
    
    home_team = match_data.get("home_name", "")
    away_team = match_data.get("away_name", "")
    competition = match_data.get("competition", "Premier League")
    
    print(f"\n📋 比赛: {home_team} vs {away_team}")
    print(f"📋 联赛: {competition}")
    
    print("\n📋 获取积分榜...")
    standings = await client.get_standings(competition)
    
    home_position = None
    away_position = None
    home_points = 0
    away_points = 0
    
    if standings:
        for s in standings:
            if s.get("team_name") == home_team:
                home_position = s.get("position")
                home_points = s.get("points", 0)
            if s.get("team_name") == away_team:
                away_position = s.get("position")
                away_points = s.get("points", 0)
        print(f"   主队排名: {home_position or '未知'} ({home_points} pts)")
        print(f"   客队排名: {away_position or '未知'} ({away_points} pts)")
    
    match_info = MatchInfo(
        match_id=str(match_data.get("match_id", "unknown")),
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        match_type=MatchType.A,
        data_quality=DataQualityLevel.MEDIUM,
        missing_data=["xg_data", "odds_data"],
    )
    
    home_stats = TeamStats(
        team_name=home_team,
        league_position=home_position,
        ppg=round(home_points / 30, 2) if home_points else 1.5,
    )
    
    away_stats = TeamStats(
        team_name=away_team,
        league_position=away_position,
        ppg=round(away_points / 30, 2) if away_points else 1.3,
    )
    
    data_quality = DataQuality(
        missing_fields=["xg_data", "odds_data", "elo_data"],
        quality_level=DataQualityLevel.LOW,
        confidence_penalty=15,
    )
    
    analysis_input = AnalysisInput(
        match_info=match_info,
        home_stats=home_stats,
        away_stats=away_stats,
        data_quality=data_quality,
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


async def main():
    print("\n" + "=" * 60)
    print("🧪 Goalcast AI - 完整测试流程")
    print("=" * 60)
    
    print(f"\n📋 LLM Provider: {settings.LLM_PROVIDER}")
    print(f"📋 LLM Model: {settings.LLM_MODEL}")
    
    matches = await get_upcoming_matches()
    
    if not matches:
        print("\n❌ 没有找到比赛，使用模拟数据测试...")
        from scripts.test_analysis import create_mock_analysis_input
        analysis_input = create_mock_analysis_input()
        
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build(analysis_input)
        
        runner = AnalysisRunner()
        response = await runner.run(prompt)
        
        if response:
            parser = OutputParser()
            output = parser.parse(response)
            if output:
                formatted = OutputFormatter.format_terminal(output.model_dump())
                print(formatted)
        return
    
    print("\n" + "-" * 60)
    print("选择要分析的比赛 (输入编号，或按 Enter 分析第一场):")
    try:
        choice = input("> ").strip()
        idx = int(choice) - 1 if choice else 0
    except:
        idx = 0
    
    if 0 <= idx < len(matches):
        await analyze_match_with_football_data(matches[idx])
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    asyncio.run(main())
