from services.value_bets import compute_edge

def test_positive_edge():
    assert compute_edge(0.6, 2.0) == 10.0

def test_negative_edge():
    assert compute_edge(0.3, 2.0) == -20.0

def test_none_inputs():
    assert compute_edge(None, 2.0) is None
    assert compute_edge(0.6, None) is None

def test_zero_odds():
    assert compute_edge(0.5, 0.0) is None
