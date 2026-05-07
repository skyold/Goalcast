from agents.core.fixture_merger import merge_fixtures
from provider.models import ProviderFixture


def _pf(provider, fid, home, away, kickoff):
    return ProviderFixture(provider=provider, fixture_id=fid,
                           home_team=home, away_team=away, kickoff_unix=kickoff)


def test_single_provider_single_match():
    result = merge_fixtures([("sportmonks", [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)])])
    assert len(result) == 1
    assert result[0].provider_ids == {"sportmonks": 100}
    assert result[0].home_team == "Arsenal"


def test_two_providers_same_match_merges():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746001800)]  # 30min offset
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1
    assert result[0].provider_ids == {"sportmonks": 100, "oddalerts": 999}


def test_time_within_one_hour_merges():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746003500)]  # 58min offset
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1


def test_time_over_one_hour_no_merge():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 999, "Arsenal", "Chelsea", 1746003600)]  # exactly 1h → different bucket
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 2


def test_different_matches_not_merged():
    sm = [_pf("sportmonks", 100, "Arsenal", "Chelsea", 1746000000)]
    oa = [_pf("oddalerts", 200, "Liverpool", "Man City", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 2


def test_accented_names_merge():
    sm = [_pf("sportmonks", 100, "Atletico Madrid", "Barcelona", 1746000000)]
    oa = [_pf("oddalerts", 999, "Atlético Madrid", "FC Barcelona", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert len(result) == 1


def test_home_team_from_priority_provider():
    sm = [_pf("sportmonks", 100, "Atletico Madrid", "Barcelona", 1746000000)]
    oa = [_pf("oddalerts", 999, "Atlético Madrid", "FC Barcelona", 1746000000)]
    result = merge_fixtures([("sportmonks", sm), ("oddalerts", oa)])
    assert result[0].home_team == "Atletico Madrid"


def test_only_oddalerts_fixture():
    oa = [_pf("oddalerts", 999, "Liverpool", "Man City", 1746000000)]
    result = merge_fixtures([("sportmonks", []), ("oddalerts", oa)])
    assert len(result) == 1
    assert result[0].provider_ids == {"oddalerts": 999}


def test_empty_inputs():
    result = merge_fixtures([("sportmonks", []), ("oddalerts", [])])
    assert result == []
