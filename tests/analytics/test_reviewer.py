from analytics.reviewer import review


def test_pass_strong():
    assert review({"pick": "H", "ev": 0.05, "confidence_stars": 4}) == "pass"


def test_fail_low_ev():
    assert review({"pick": "H", "ev": 0.005, "confidence_stars": 4}) == "fail"


def test_fail_low_confidence():
    assert review({"pick": "H", "ev": 0.05, "confidence_stars": 2}) == "fail"


def test_skip_suspicious_ev():
    assert review({"pick": "H", "ev": 0.50, "confidence_stars": 5}) == "skip"


def test_none_on_missing():
    assert review(None) is None
    assert review({}) is None
    assert review({"pick": "H"}) is None
