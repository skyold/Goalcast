import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import FootyStatsProvider, FootballDataProvider
from datasource import MatchDataSource, registry, Match
from aggregator.match_builder import MatchBuilder
from engine.prompt import PromptBuilder
from engine.runner import AnalysisRunner
from engine.parser import OutputParser
from utils.formatter import OutputFormatter
from utils.logger import logger


async def find_upcoming_matches(hours=72):
    fd = FootballDataProvider()
    
    today = datetime.now()
    date_from = today.strftime('%Y-%m-%d')
    date_to = (today + timedelta(days=7)).strftime('%Y-%m-%d')

    leagues = ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']
    all_matches = []

    for league in leagues:
        try:
            result = await fd.get_matches(league, date_from, date_to)
            if result and result.get('matches'):
                for m in result['matches']:
                    home = m.get('homeTeam', {}).get('name', '?')
                    away = m.get('awayTeam', {}).get('name', '?')
                    status = m.get('status', '?')
                    match_id = m.get('id', '?')
                    date = m.get('utcDate', '?')
                    all_matches.append({
                        'league': league,
                        'home': home,
                        'away': away,
                        'status': status,
                        'id': match_id,
                        'date': date,
                    })
        except Exception as e:
            logger.warning(f"Error fetching {league}: {e}")

    return all_matches


async def find_recent_matches(days=7):
    fd = FootballDataProvider()
    
    today = datetime.now()
    date_from = (today - timedelta(days=days)).strftime('%Y-%m-%d')
    date_to = today.strftime('%Y-%m-%d')

    leagues = ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']
    all_matches = []

    for league in leagues:
        try:
            result = await fd.get_matches(league, date_from, date_to)
            if result and result.get('matches'):
                for m in result['matches']:
                    home = m.get('homeTeam', {}).get('name', '?')
                    away = m.get('awayTeam', {}).get('name', '?')
                    status = m.get('status', '?')
                    match_id = m.get('id', '?')
                    date = m.get('utcDate', '?')
                    all_matches.append({
                        'league': league,
                        'home': home,
                        'away': away,
                        'status': status,
                        'id': match_id,
                        'date': date,
                    })
        except Exception as e:
            logger.warning(f"Error fetching {league}: {e}")

    return all_matches


async def analyze_match(match_info, dry_run=False):
    match_id = str(match_info['id'])
    home = match_info['home']
    away = match_info['away']
    league = match_info['league']

    logger.info(f"Analyzing: {home} vs {away} (ID: {match_id})")

    builder = MatchBuilder()
    analysis_input = await builder.build(match_id)

    if not analysis_input:
        logger.warning(f"Could not build analysis for {match_id}")
        return None

    if dry_run:
        input_dict = analysis_input.model_dump()
        prompt_builder = PromptBuilder()
        prompt = prompt_builder.build(analysis_input)
        return {
            'match': match_info,
            'input': input_dict,
            'prompt_length': len(prompt),
            'dry_run': True,
        }

    logger.info(f"Calling LLM for {match_id}...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)

    runner = AnalysisRunner()
    response = await runner.run(prompt)

    if not response:
        logger.error(f"LLM call failed for {match_id}")
        return None

    parser = OutputParser()
    output = parser.parse(response)

    return {
        'match': match_info,
        'input': analysis_input.model_dump(),
        'output': output.model_dump() if output else None,
        'raw_response': response,
        'timestamp': datetime.now().isoformat(),
    }


async def main():
    print("=" * 70)
    print("GOALCAST AI - MATCH FINDER & ANALYZER")
    print("=" * 70)
    print()

    print("📡 Searching for upcoming matches (next 72 hours)...")
    upcoming = await find_upcoming_matches(hours=72)

    if upcoming:
        print(f"\n✅ Found {len(upcoming)} upcoming matches:")
        for i, m in enumerate(upcoming, 1):
            print(f"  {i}. {m['home']} vs {m['away']} ({m['league']})")
            print(f"     ID: {m['id']} | Status: {m['status']} | Date: {m['date']}")
    else:
        print("\n⚠️ No upcoming matches found in next 72 hours.")

    print("\n" + "-" * 70)
    print("📊 Searching for recent matches (last 7 days)...")
    recent = await find_recent_matches(days=7)

    if recent:
        print(f"\n✅ Found {len(recent)} recent matches:")
        for i, m in enumerate(recent[:10], 1):
            print(f"  {i}. {m['home']} vs {m['away']} ({m['status']})")
            print(f"     ID: {m['id']} | Date: {m['date']}")

    if not recent and not upcoming:
        print("\n❌ No matches found. Check API configuration.")
        return

    print("\n" + "=" * 70)
    print("🎯 SELECTING MATCH FOR ANALYSIS")
    print("=" * 70)

    target = None
    if upcoming:
        target = upcoming[0]
        print(f"\n📌 Selected UPcoming match: {target['home']} vs {target['away']}")
    else:
        target = recent[0]
        print(f"\n📌 Selected RECENT match: {target['home']} vs {target['away']}")
        print("   (No upcoming matches available, using recent match)")

    print(f"\n   League: {target['league']}")
    print(f"   Match ID: {target['id']}")
    print(f"   Status: {target['status']}")
    print(f"   Date: {target['date']}")

    print("\n" + "=" * 70)
    print("🔍 RUNNING ANALYSIS (DRY RUN - No LLM Call)")
    print("=" * 70)

    result = await analyze_match(target, dry_run=True)

    if result and result.get('dry_run'):
        print(f"\n✅ Dry run successful!")
        print(f"\n📋 Input Data Summary:")
        input_data = result.get('input', {})
        match_info = input_data.get('match_info', {})
        home_stats = input_data.get('home_stats', {})
        away_stats = input_data.get('away_stats', {})

        print(f"   Match: {match_info.get('home_team', '?')} vs {match_info.get('away_team', '?')}")
        print(f"   Competition: {match_info.get('competition', '?')}")
        print(f"   Data Quality: {match_info.get('data_quality', '?')}")
        print(f"   Missing Data: {match_info.get('missing_data', [])[:5]}...")

        print(f"\n📊 Home Team Stats:")
        print(f"   Team: {home_stats.get('team_name', '?')}")
        print(f"   xG Home: {home_stats.get('xg_home', 'N/A')}")
        print(f"   xG Away: {home_stats.get('xg_away', 'N/A')}")
        print(f"   Elo: {home_stats.get('elo', 'N/A')}")

        print(f"\n📊 Away Team Stats:")
        print(f"   Team: {away_stats.get('team_name', '?')}")
        print(f"   xG Home: {away_stats.get('xg_home', 'N/A')}")
        print(f"   xG Away: {away_stats.get('xg_away', 'N/A')}")
        print(f"   Elo: {away_stats.get('elo', 'N/A')}")

        print(f"\n📝 Generated Prompt Length: {result.get('prompt_length', 0)} characters")

        odds = input_data.get('odds')
        if odds:
            print(f"\n💰 Odds Data:")
            print(f"   Home: {odds.get('opening_home', 'N/A')}")
            print(f"   Draw: {odds.get('opening_draw', 'N/A')}")
            print(f"   Away: {odds.get('opening_away', 'N/A')}")

        context = input_data.get('context', {})
        if context:
            print(f"\n🏥 Context:")
            print(f"   Home Injuries: {context.get('injuries_home', [])}")
            print(f"   Away Injuries: {context.get('injuries_away', [])}")

    print("\n" + "=" * 70)
    print("To run full analysis with LLM, use:")
    print("  python scripts/analyze_match.py --match_id <ID>")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
