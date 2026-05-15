import pytest

@pytest.fixture(autouse=True)
def use_tmp_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GOALCAST_DB_PATH", str(tmp_path / "test.db"))
    import importlib, database
    importlib.reload(database)
