#!/usr/bin/env python3

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import FootballDataProvider
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


async def analyze_match_from_football_data(match_data, dry_run=True):
    home_team = match_data.get('homeTeam', {}).get('name', 'Unknown')
    away_team = match_data.get('awayTeam', {}).get('name', 'Unknown')
    competition = match_data.get('competition', {}).get('name', 'Unknown')
    match_id = match_data.get('id', 'N/A')
    utc_date = match_data.get('utcDate', '')

    logger.info(f"Analyzing: {home_team} vs {away_team}")

    home_stats = TeamStats(
        team_id=str(match_data.get('homeTeam', {}).get('id', '')),
        team_name=home_team,
        xg_home=1.5,
        xg_away=1.3,
        recent_form=['W', 'D', 'W', 'L', 'W'],
        elo=1750.0,
    )

    away_stats = TeamStats(
        team_id=str(match_data.get('awayTeam', {}).get('id', '')),
        team_name=away_team,
        xg_home=1.4,
        xg_away=1.2,
        recent_form=['W', 'W', 'D', 'W', 'L'],
        elo=1720.0,
    )

    odds = OddsData(
        opening_home=2.10,
        opening_draw=3.40,
        opening_away=3.50,
        current_home=2.05,
        current_draw=3.45,
        current_away=3.60,
    )

    match_info = MatchInfo(
        match_id=str(match_id),
        home_team=home_team,
        away_team=away_team,
        competition=competition,
        match_type=MatchType.A,
        missing_data=[],
        data_quality=DataQualityLevel.MEDIUM,
    )

    context = ContextData(
        injuries_home=[],
        injuries_away=[],
        motivation_notes="Standard league match",
    )

    analysis_input = AnalysisInput(
        match_info=match_info,
        home_stats=home_stats,
        away_stats=away_stats,
        odds=odds,
        context=context,
        weather=None,
        data_quality=DataQuality(
            missing_fields=[],
            quality_level=DataQualityLevel.MEDIUM,
            confidence_penalty=5,
        ),
    )

    logger.info("Building prompt...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)

    if dry_run:
        logger.info("DRY RUN - Returning prompt and input data")
        return {
            'match': {
                'home': home_team,
                'away': away_team,
                'competition': competition,
                'match_id': match_id,
                'date': utc_date,
            },
            'input': analysis_input.model_dump(),
            'prompt': prompt,
            'prompt_length': len(prompt),
            'dry_run': True,
        }

    logger.info("Calling LLM...")
    runner = AnalysisRunner()
    response = await runner.run(prompt)

    if not response:
        logger.error("LLM call failed")
        return None

    parser = OutputParser()
    output = parser.parse(response)

    return {
        'match': {
            'home': home_team,
            'away': away_team,
            'competition': competition,
            'match_id': match_id,
            'date': utc_date,
        },
        'input': analysis_input.model_dump(),
        'output': output.model_dump() if output else None,
        'raw_response': response,
        'timestamp': datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("GOALCAST AI - FOOTBALL-DATA INTEGRATION TEST")
    print("=" * 70)
    print()

    fd = FootballDataProvider()

    print("📡 Fetching recent Premier League matches...")
    print()

    today = datetime.now()
    date_from = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')

    result = await fd.get_matches('Premier League', date_from, date_to)

    if not result or not result.get('matches'):
        print("❌ No matches found")
        return

    matches = result['matches']
    print(f"✅ Found {len(matches)} matches\n")

    for i, m in enumerate(matches, 1):
        home = m.get('homeTeam', {}).get('name', '?')
        away = m.get('awayTeam', {}).get('name', '?')
        status = m.get('status', '?')
        date = m.get('utcDate', '?')
        match_id = m.get('id', '?')
        print(f"{i}. {home} vs {away}")
        print(f"   Status: {status} | ID: {match_id} | Date: {date[:10]}")

    print()
    print("=" * 70)
    print("🎯 RUNNING ANALYSIS ON FIRST MATCH (DRY RUN)")
    print("=" * 70)
    print()

    analysis = await analyze_match_from_football_data(matches[0], dry_run=True)

    if analysis and analysis.get('dry_run'):
        print("✅ Analysis successful!\n")

        match = analysis.get('match', {})
        print(f"📋 Match: {match.get('home')} vs {match.get('away')}")
        print(f"   Competition: {match.get('competition')}")
        print(f"   Match ID: {match.get('match_id')}")
        print(f"   Date: {match.get('date')}")

        print()
        print("📊 Input Data:")
        input_data = analysis.get('input', {})

        home_stats = input_data.get('home_stats', {})
        away_stats = input_data.get('away_stats', {})

        print(f"   Home Team: {home_stats.get('team_name')}")
        print(f"   Home xG Home: {home_stats.get('xg_home')}")
        print(f"   Home Elo: {home_stats.get('elo')}")
        print(f"   Home Recent Form: {home_stats.get('recent_form')}")

        print()
        print(f"   Away Team: {away_stats.get('team_name')}")
        print(f"   Away xG Away: {away_stats.get('xg_away')}")
        print(f"   Away Elo: {away_stats.get('elo')}")
        print(f"   Away Recent Form: {away_stats.get('recent_form')}")

        odds = input_data.get('odds', {})
        print()
        print("💰 Odds:")
        print(f"   Opening: {odds.get('opening_home')} / {odds.get('opening_draw')} / {odds.get('opening_away')}")
        print(f"   Current: {odds.get('current_home')} / {odds.get('current_draw')} / {odds.get('current_away')}")

        print()
        print(f"📝 Generated Prompt Length: {analysis.get('prompt_length')} characters")
        print()
        print("-" * 70)
        print("📄 PROMPT PREVIEW (first 1000 chars):")
        print("-" * 70)
        print(analysis.get('prompt', '')[:1000])
        print("...")
        print("-" * 70)

    print()
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("To run full analysis with LLM, modify the script:")
    print("  analysis = await analyze_match_from_football_data(matches[0], dry_run=False)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
