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
    TransfermarktProvider,
)
from datasource import (
    MatchDataSource,
    TeamDataSource,
    StandingsDataSource,
    EloDataSource,
    InjuryDataSource,
    registry,
    Injury,
    InjurySeverity,
    Lineup,
    compute_xg_adjustment,
    classify_player_importance,
)
from datasource.types import DataSourceType, Match, Team, Odds, Elo

load_dotenv()


async def test_full_flow():
    print("=" * 70)
    print("Goalcast Full Architecture Test - Phase 2.5")
    print("=" * 70)
    
    fs_provider = FootyStatsProvider()
    fd_provider = FootballDataProvider()
    understat_provider = UnderstatProvider()
    elo_provider = ClubEloProvider()
    tm_provider = TransfermarktProvider()
    
    print("\n[1] Testing All Providers...")
    providers = [
        ("FootyStats", fs_provider),
        ("Football-Data", fd_provider),
        ("Understat", understat_provider),
        ("ClubElo", elo_provider),
        ("Transfermarkt", tm_provider),
    ]
    for name, provider in providers:
        available = await provider.is_available()
        print(f"  {name}: {'✓' if available else '✗'}")
    
    print("\n[2] Creating All DataSources...")
    
    match_ds = MatchDataSource(providers=[fs_provider, fd_provider])
    team_ds = TeamDataSource(providers=[fs_provider, understat_provider, elo_provider])
    standings_ds = StandingsDataSource(providers=[fs_provider, fd_provider])
    elo_ds = EloDataSource(providers=[elo_provider])
    injury_ds = InjuryDataSource(providers=[tm_provider])
    
    data_sources = [
        ("MatchDataSource", match_ds),
        ("TeamDataSource", team_ds),
        ("StandingsDataSource", standings_ds),
        ("EloDataSource", elo_ds),
        ("InjuryDataSource", injury_ds),
    ]
    for name, ds in data_sources:
        print(f"  {name}: {ds}")
    
    print("\n[3] Registering All DataSources...")
    for _, ds in data_sources:
        registry.register(ds)
    
    print(f"  Registered types: {list(registry.list_all().keys())}")
    
    print("\n[4] Testing MatchDataSource with Provider Fallback...")
    upcoming = await match_ds.fetch_upcoming("Premier League", days=7)
    if upcoming:
        print(f"  Found {len(upcoming)} upcoming matches")
        for m in upcoming[:3]:
            print(f"    - {m.home_team} vs {m.away_team}")
            if m.first_leg_score:
                print(f"      First leg: {m.first_leg_score}")
    else:
        print("  No upcoming matches found (trying fetch by ID)...")
        match = await match_ds.fetch(match_id="12345")
        if match:
            print(f"  Match: {match}")
    
    print("\n[5] Testing StandingsDataSource...")
    standings = await standings_ds.fetch(competition="Premier League")
    if standings:
        print(f"  Found {len(standings)} teams")
        for s in standings[:5]:
            print(f"    {s.position}. {s.team_name} - {s.points} pts")
    
    print("\n[6] Testing EloDataSource...")
    elo = await elo_ds.fetch(team_name="Arsenal")
    if elo:
        print(f"  Arsenal Elo: {elo.elo:.1f}")
        win_prob = elo.calculate_win_probability(1750)
        print(f"  Win probability vs Elo 1750: {win_prob:.1%}")
    else:
        print("  Elo data not available (API issue)")
    
    print("\n[7] Testing InjuryDataSource...")
    injuries = await injury_ds.fetch(team_name="Arsenal")
    if injuries:
        print(f"  Found {len(injuries)} injuries/suspensions")
        for inj in injuries[:3]:
            print(f"    - {inj.player_name} ({inj.severity.value}): {inj.injury_type}")
            print(f"      xG adjustment: {inj.calculate_xg_adjustment()}")
    else:
        print("  No injury data found (Transfermarkt requires HTML parsing)")
    
    print("\n[8] Testing Injury Data Types...")
    test_injuries = [
        Injury("Haaland", "Man City", "Ankle", InjurySeverity.MEDIUM_TERM, position="ST", is_key_player=True),
        Injury("De Bruyne", "Man City", "Muscle", InjurySeverity.SHORT_TERM, position="MF", is_key_player=True),
        Injury("Backup GK", "Man City", "Hand", InjurySeverity.LONG_TERM, position="GK", is_key_player=False),
    ]
    
    classified = classify_player_importance(test_injuries)
    total_adj = compute_xg_adjustment(classified)
    
    print(f"  Test injuries: {len(test_injuries)}")
    for inj in classified:
        print(f"    - {inj.player_name}: key_player={inj.is_key_player}, adj={inj.calculate_xg_adjustment()}")
    print(f"  Total xG adjustment: {total_adj}")
    
    print("\n[9] Testing Odds with Movement...")
    opening = Odds(home=2.10, draw=3.40, away=3.50, bookmaker="Bet365")
    current = Odds(home=1.85, draw=3.60, away=4.20, bookmaker="Bet365", opening_odds=opening)
    
    current.calculate_implied_probabilities()
    movement = current.calculate_movement()
    
    print(f"  Opening: {opening.home}/{opening.draw}/{opening.away}")
    print(f"  Current: {current.home}/{current.draw}/{current.away}")
    print(f"  Movement: {movement}")
    print(f"  Implied probs: H={current.home_prob:.1%} D={current.draw_prob:.1%} A={current.away_prob:.1%}")
    
    print("\n[10] Testing Match with First Leg Score...")
    match = Match(
        match_id="cl_2024_sf",
        home_team="Real Madrid",
        away_team="Bayern Munich",
        competition="Champions League",
        match_type=datasource.types.MatchType.TWO_LEG,
        first_leg_score=(2, 2),
    )
    print(f"  Match: {match.home_team} vs {match.away_team}")
    print(f"  Type: {match.match_type.value} (Two-legged)")
    print(f"  First leg: {match.first_leg_score}")
    
    print("\n[11] Testing Team with New Fields...")
    team = Team(
        team_id="arsenal",
        name="Arsenal",
        position=1,
        points=70,
        dangerous_attacks=52,
        schedule_density_7d=2,
        injury_details=test_injuries,
    )
    print(f"  Team: {team.name} (#{team.position})")
    print(f"  Dangerous attacks: {team.dangerous_attacks}")
    print(f"  Schedule density (7d): {team.schedule_density_7d}")
    print(f"  Injury details: {len(team.injury_details)} players")
    
    print("\n[12] Testing Lineup Data Type...")
    lineup = Lineup(
        team_id="arsenal",
        team_name="Arsenal",
        match_id="12345",
        formation="4-3-3",
        starting_xi=["Raya", "White", "Saliba", "Gabriel", "Zinchenko",
                     "Odegaard", "Rice", "Havertz", "Saka", "Martinelli", "Jesus"],
        is_confirmed=True,
        source="official",
    )
    print(f"  Lineup: {lineup.team_name} ({lineup.formation})")
    print(f"  Status: {'Confirmed' if lineup.is_confirmed else 'Expected'}")
    print(f"  Starting XI: {len(lineup.starting_xi)} players")
    
    print("\n[13] Testing Registry Capabilities...")
    capabilities = registry.capabilities()
    for dtype, cap in capabilities.items():
        print(f"  {dtype.value}: {cap.name}")
        print(f"    Providers: {cap.providers}")
        print(f"    Params: {list(cap.params.keys())}")
    
    print("\n" + "=" * 70)
    print("All tests completed successfully!")
    print("=" * 70)
    
    for _, provider in providers:
        if hasattr(provider, 'close'):
            await provider.close()


if __name__ == "__main__":
    import datasource
    asyncio.run(test_full_flow())
