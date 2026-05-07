from provider.models import ProviderFixture, UnifiedFixture

def test_provider_fixture_defaults():
    f = ProviderFixture(
        provider="sportmonks",
        fixture_id=1,
        home_team="Arsenal",
        away_team="Chelsea",
        kickoff_unix=1746000000,
    )
    assert f.league_name is None
    assert f.raw == {}
    assert f.provider == "sportmonks"

def test_unified_fixture_missing_provider_returns_none():
    u = UnifiedFixture(
        home_team="Arsenal",
        away_team="Chelsea",
        kickoff_unix=1746000000,
        provider_ids={"sportmonks": 100},
    )
    assert u.provider_ids.get("oddalerts") is None
    assert u.provider_ids["sportmonks"] == 100

def test_unified_fixture_default_provider_ids_empty():
    u = UnifiedFixture(home_team="A", away_team="B", kickoff_unix=1000)
    assert u.provider_ids == {}
