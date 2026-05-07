from utils.normalize import normalize_team_name

def test_removes_accents():
    assert normalize_team_name("Atlético Madrid") == "atleticomadrid"

def test_removes_spaces():
    assert normalize_team_name("Borussia Dortmund") == "borussiadortmund"

def test_removes_hyphens():
    assert normalize_team_name("Paris Saint-Germain") == "parissaintgermain"

def test_lowercase():
    assert normalize_team_name("ARSENAL") == "arsenal"

def test_non_ascii_stripped():
    assert normalize_team_name("São Paulo") == "saopaulo"

def test_empty_string():
    assert normalize_team_name("") == ""
