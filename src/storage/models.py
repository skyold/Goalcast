from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

Base = declarative_base()


class Analysis(Base):
    __tablename__ = "analyses"

    analysis_id = Column(String(36), primary_key=True)
    match_id = Column(String(50), nullable=False, index=True)
    home_team = Column(String(100))
    away_team = Column(String(100))
    competition = Column(String(100))
    prompt_version = Column(String(20))
    input_json = Column(Text)
    output_json = Column(Text)
    confidence = Column(Integer)
    ev = Column(Float)
    risk_adjusted_ev = Column(Float)
    best_bet = Column(String(50))
    bet_rating = Column(String(20))
    data_quality = Column(String(20))
    actual_result = Column(String(20), nullable=True)
    actual_score = Column(String(10), nullable=True)
    ev_realized = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Match(Base):
    __tablename__ = "matches"

    match_id = Column(String(50), primary_key=True)
    home_team = Column(String(100))
    away_team = Column(String(100))
    competition = Column(String(100))
    kickoff_dt = Column(DateTime, nullable=True)
    status = Column(String(20))
    home_score = Column(Integer, nullable=True)
    away_score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DataQualityLog(Base):
    __tablename__ = "data_quality_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String(36), ForeignKey("analyses.analysis_id"))
    missing_field = Column(String(100))
    impact = Column(String(50))
    created_at = Column(DateTime, default=datetime.now)


class DatabaseManager:
    def __init__(self, database_url: str = "sqlite:///data/db/goalcast.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._initialize()

    def _initialize(self):
        db_path = self.database_url.replace("sqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            self.database_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.SessionLocal()

    def close(self):
        if self.engine:
            self.engine.dispose()


_db_manager = None


def get_db_manager(database_url: str = "sqlite:///data/db/goalcast.db") -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(database_url)
    return _db_manager
