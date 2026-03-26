import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider.football_data.client import FootballDataProvider

async def test():
    fd = FootballDataProvider()

    today = datetime.now()
    date_from = today.strftime('%Y-%m-%d')
    date_to = (today + timedelta(days=7)).strftime('%Y-%m-%d')

    print(f"Today: {today}")
    print(f"Fetching matches from {date_from} to {date_to}...")
    print()

    leagues = ['Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1']
    all_matches = []

    for league in leagues:
        try:
            result = await fd.get_matches(league, date_from, date_to)
            if result:
                matches = result.get('matches', [])
                if matches:
                    print(f'=== {league}: {len(matches)} matches ===')
                    for m in matches:
                        home = m.get('homeTeam', {}).get('name', '?')
                        away = m.get('awayTeam', {}).get('name', '?')
                        status = m.get('status', '?')
                        date = m.get('utcDate', '?')
                        match_id = m.get('id', '?')
                        print(f'  {home} vs {away}')
                        print(f'    Status: {status} | ID: {match_id}')
                        print(f'    Date: {date}')
                        all_matches.append({
                            'league': league,
                            'home': home,
                            'away': away,
                            'status': status,
                            'id': match_id,
                            'date': date,
                        })
                    print()
        except Exception as e:
            print(f'{league}: Error - {e}')

    print("=" * 60)
    print(f"Total upcoming matches found: {len(all_matches)}")
    print("=" * 60)

    if all_matches:
        print("\nUpcoming matches:")
        for i, m in enumerate(all_matches, 1):
            print(f"{i}. {m['home']} vs {m['away']} ({m['league']})")
            print(f"   ID: {m['id']} | Status: {m['status']}")
    else:
        print("\nNo upcoming matches found in the next 7 days.")
        print("\nLast 7 days matches (for reference):")
        date_from = (today - timedelta(days=7)).strftime('%Y-%m-%d')
        date_to = today.strftime('%Y-%m-%d')
        for league in leagues[:1]:
            result = await fd.get_matches(league, date_from, date_to)
            if result and result.get('matches'):
                for m in result.get('matches', [])[:3]:
                    home = m.get('homeTeam', {}).get('name', '?')
                    away = m.get('awayTeam', {}).get('name', '?')
                    status = m.get('status', '?')
                    match_id = m.get('id', '?')
                    print(f"  - {home} vs {away} ({status}) - ID: {match_id}")

asyncio.run(test())
