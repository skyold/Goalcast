import pytest
from agents.scheduler import start_scheduler

def test_scheduler_initialization(monkeypatch):
    class MockScheduler:
        def __init__(self):
            self.job_added = False
            self.started = False
        def add_job(self, *args, **kwargs):
            self.job_added = True
        def start(self):
            self.started = True
            
    mock_instance = MockScheduler()
    monkeypatch.setattr("agents.scheduler.AsyncIOScheduler", lambda: mock_instance)
    
    scheduler = start_scheduler()
    assert mock_instance.started
    assert mock_instance.job_added
