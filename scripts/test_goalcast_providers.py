#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import (
    FootyStatsProvider,
    FootballDataProvider,
    UnderstatProvider,
    ClubEloProvider,
    OddsProvider,
    WeatherProvider,
    TransfermarktProvider,
)


async def test_all_providers():
    results = []

    print("=" * 70)
    print("GOALCAST AI - PROVIDER TESTING")
    print("=" * 70)
    print()

    # Test FootyStatsProvider
    print("=== Testing FootyStatsProvider ===")
    try:
        fs = FootyStatsProvider()
        available = await fs.is_available()
        print(f"  Available: {available}")
        print(f"  API Key configured: {bool(fs.api_key)}")

        if available:
            test_match = await fs.get_match("12345")
            print(f"  get_match('12345'): {'OK' if test_match else 'No data'}")
            print(f"  Status: {'✅ WORKING' if test_match else '⚠️ NO DATA'}")
            results.append(('FootyStatsProvider', '✅ WORKING' if test_match else '⚠️ NO DATA', bool(fs.api_key)))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('FootyStatsProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('FootyStatsProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test FootballDataProvider
    print("=== Testing FootballDataProvider ===")
    try:
        fd = FootballDataProvider()
        available = await fd.is_available()
        print(f"  Available: {available}")
        print(f"  API Key configured: {bool(fd.api_key)}")

        if available:
            today = datetime.now()
            date_from = (today - timedelta(days=7)).strftime('%Y-%m-%d')
            date_to = today.strftime('%Y-%m-%d')

            matches = await fd.get_matches('Premier League', date_from, date_to)
            print(f"  get_matches(Premier League, {date_from}, {date_to}): {len(matches.get('matches', []) if matches else 0)} matches")
            print(f"  Status: {'✅ WORKING' if matches else '⚠️ NO DATA'}")
            results.append(('FootballDataProvider', '✅ WORKING' if matches else '⚠️ NO DATA', bool(fd.api_key)))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('FootballDataProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('FootballDataProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test UnderstatProvider
    print("=== Testing UnderstatProvider ===")
    try:
        us = UnderstatProvider()
        available = await us.is_available()
        print(f"  Available: {available}")

        if available:
            matches = await us.get_team_matches("Arsenal", "Premier League", "2024")
            print(f"  get_team_matches(Arsenal, Premier League, 2024): {len(matches) if matches else 0} matches")
            print(f"  Status: {'✅ WORKING' if matches else '⚠️ NO DATA'}")
            results.append(('UnderstatProvider', '✅ WORKING' if matches else '⚠️ NO DATA', True))
        else:
            print(f"  Status: ⚠️ UNAVAILABLE")
            results.append(('UnderstatProvider', '⚠️ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('UnderstatProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test ClubEloProvider
    print("=== Testing ClubEloProvider ===")
    try:
        ce = ClubEloProvider()
        available = await ce.is_available()
        print(f"  Available: {available}")

        if available:
            elo = await ce.get_elo("Arsenal")
            print(f"  get_elo(Arsenal): {elo}")
            print(f"  Status: {'✅ WORKING' if elo else '⚠️ NO DATA'}")
            results.append(('ClubEloProvider', '✅ WORKING' if elo else '⚠️ NO DATA', True))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('ClubEloProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('ClubEloProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test OddsProvider
    print("=== Testing OddsProvider ===")
    try:
        op = OddsProvider()
        available = await op.is_available()
        print(f"  Available: {available}")
        print(f"  API Key configured: {bool(op.api_key)}")

        if available:
            odds = await op.get_odds("soccer_ew_league", "12345")
            print(f"  get_odds(soccer_ew_league, 12345): {'OK' if odds else 'No data'}")
            print(f"  Status: {'✅ WORKING' if odds else '⚠️ NO DATA'}")
            results.append(('OddsProvider', '✅ WORKING' if odds else '⚠️ NO DATA', bool(op.api_key)))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('OddsProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('OddsProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test WeatherProvider
    print("=== Testing WeatherProvider ===")
    try:
        wp = WeatherProvider()
        available = await wp.is_available()
        print(f"  Available: {available}")
        print(f"  API Key configured: {bool(wp.api_key)}")

        if available:
            weather = await wp.get_weather(51.5074, -0.1278)
            print(f"  get_weather(51.5074, -0.1278): {'OK' if weather else 'No data'}")
            print(f"  Status: {'✅ WORKING' if weather else '⚠️ NO DATA'}")
            results.append(('WeatherProvider', '✅ WORKING' if weather else '⚠️ NO DATA', bool(wp.api_key)))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('WeatherProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('WeatherProvider', f'❌ ERROR: {str(e)[:30]}', False))

    print()

    # Test TransfermarktProvider
    print("=== Testing TransfermarktProvider ===")
    try:
        tm = TransfermarktProvider()
        available = await tm.is_available()
        print(f"  Available: {available}")

        if available:
            injuries = await tm.get_injuries("Arsenal")
            print(f"  get_injuries(Arsenal): {'OK' if injuries else 'No data'}")
            print(f"  Status: {'✅ WORKING' if injuries else '⚠️ NO DATA'}")
            results.append(('TransfermarktProvider', '✅ WORKING' if injuries else '⚠️ NO DATA', True))
        else:
            print(f"  Status: ❌ UNAVAILABLE")
            results.append(('TransfermarktProvider', '❌ UNAVAILABLE', False))
    except Exception as e:
        print(f"  Error: {e}")
        results.append(('TransfermarktProvider', f'❌ ERROR: {str(e)[:30]}', False))

    # Print Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Provider':25} {'Status':20} {'API Key':10}")
    print("-" * 55)
    for name, status, has_key in results:
        api_key_str = "✅ Configured" if has_key else "❌ Missing"
        print(f"{name:25} {status:20} {api_key_str:10}")
    print()

    working_count = sum(1 for _, s, _ in results if '✅' in s)
    print(f"Working: {working_count}/{len(results)}")

    return results


if __name__ == "__main__":
    asyncio.run(test_all_providers())
