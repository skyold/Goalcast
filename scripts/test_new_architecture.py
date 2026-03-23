import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from dotenv import load_dotenv
from provider import (
    FootyStatsProvider,
    FootballDataProvider,
    UnderstatProvider,
    ClubEloProvider,
)
from datasource import (
    MatchDataSource,
    TeamDataSource,
    StandingsDataSource,
    EloDataSource,
    registry,
)
from datasource.types import DataSourceType

load_dotenv()


async def test_new_architecture():
    print("=" * 60)
    print("Goalcast New Architecture Test")
    print("=" * 60)
    
    fs_provider = FootyStatsProvider()
    fd_provider = FootballDataProvider()
    understat_provider = UnderstatProvider()
    elo_provider = ClubEloProvider()
    
    print("\n[1] Testing Providers...")
    print(f"  FootyStats available: {await fs_provider.is_available()}")
    print(f"  Football-Data available: {await fd_provider.is_available()}")
    print(f"  Understat available: {await understat_provider.is_available()}")
    print(f"  ClubElo available: {await elo_provider.is_available()}")
    
    print("\n[2] Creating DataSources...")
    
    match_ds = MatchDataSource(providers=[fs_provider, fd_provider])
    team_ds = TeamDataSource(providers=[fs_provider, understat_provider])
    standings_ds = StandingsDataSource(providers=[fs_provider, fd_provider])
    elo_ds = EloDataSource(providers=[elo_provider])
    
    print(f"  MatchDataSource: {match_ds}")
    print(f"  TeamDataSource: {team_ds}")
    print(f"  StandingsDataSource: {standings_ds}")
    print(f"  EloDataSource: {elo_ds}")
    
    print("\n[3] Registering DataSources...")
    registry.register(match_ds)
    registry.register(team_ds)
    registry.register(standings_ds)
    registry.register(elo_ds)
    
    print(f"  Registered: {registry.list_all()}")
    
    print("\n[4] Testing MatchDataSource...")
    upcoming = await match_ds.fetch_upcoming("Premier League", days=7)
    if upcoming:
        print(f"  Found {len(upcoming)} upcoming matches")
        for m in upcoming[:3]:
            print(f"    - {m.home_team} vs {m.away_team} ({m.status.value})")
    else:
        print("  No upcoming matches found")
    
    print("\n[5] Testing StandingsDataSource...")
    standings = await standings_ds.fetch(competition="Premier League")
    if standings:
        print(f"  Found {len(standings)} teams in standings")
        for s in standings[:5]:
            print(f"    {s.position}. {s.team_name} - {s.points} pts")
    else:
        print("  No standings found")
    
    print("\n[6] Testing EloDataSource...")
    elo = await elo_ds.fetch(team_name="Arsenal")
    if elo:
        print(f"  Arsenal Elo: {elo.elo:.1f}")
    else:
        print("  No Elo data found")
    
    print("\n[7] Testing Capabilities...")
    capabilities = registry.capabilities()
    for dtype, cap in capabilities.items():
        print(f"  {dtype.value}: {cap.name} (providers: {cap.providers})")
    
    print("\n[8] Testing Registry Get...")
    match_ds_from_registry = registry.get(DataSourceType.MATCH)
    print(f"  Got from registry: {match_ds_from_registry}")
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    
    await fs_provider.close()
    await fd_provider.close()
    await understat_provider.close()


if __name__ == "__main__":
    asyncio.run(test_new_architecture())
