import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from src.storage.models import (
    Analysis,
    Match,
    DataQualityLog,
    get_db_manager,
)
from utils.logger import logger


class Repository:
    def __init__(self, database_url: str = "sqlite:///data/db/goalcast.db"):
        self.db_manager = get_db_manager(database_url)

    @contextmanager
    def _session(self):
        session = self.db_manager.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def save_analysis(
        self,
        match_id: str,
        home_team: str,
        away_team: str,
        competition: str,
        prompt_version: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        confidence: int,
        ev: float,
        risk_adjusted_ev: float,
        best_bet: str,
        bet_rating: str,
        data_quality: str,
    ) -> Optional[str]:
        analysis_id = str(uuid.uuid4())

        try:
            with self._session() as session:
                analysis = Analysis(
                    analysis_id=analysis_id,
                    match_id=match_id,
                    home_team=home_team,
                    away_team=away_team,
                    competition=competition,
                    prompt_version=prompt_version,
                    input_json=json.dumps(input_data),
                    output_json=json.dumps(output_data),
                    confidence=confidence,
                    ev=ev,
                    risk_adjusted_ev=risk_adjusted_ev,
                    best_bet=best_bet,
                    bet_rating=bet_rating,
                    data_quality=data_quality,
                )
                session.add(analysis)

                missing_fields = input_data.get("data_quality", {}).get("missing_fields", [])
                for field in missing_fields:
                    log = DataQualityLog(
                        analysis_id=analysis_id,
                        missing_field=field,
                        impact="confidence_penalty",
                    )
                    session.add(log)

            logger.info(f"Analysis saved: {analysis_id}")
            return analysis_id

        except Exception as e:
            logger.error(f"Error saving analysis: {e}")
            return None

    def get_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._session() as session:
                analysis = session.query(Analysis).filter(
                    Analysis.analysis_id == analysis_id
                ).first()

                if not analysis:
                    return None

                return {
                    "analysis_id": analysis.analysis_id,
                    "match_id": analysis.match_id,
                    "home_team": analysis.home_team,
                    "away_team": analysis.away_team,
                    "competition": analysis.competition,
                    "prompt_version": analysis.prompt_version,
                    "input_json": json.loads(analysis.input_json),
                    "output_json": json.loads(analysis.output_json),
                    "confidence": analysis.confidence,
                    "ev": analysis.ev,
                    "risk_adjusted_ev": analysis.risk_adjusted_ev,
                    "best_bet": analysis.best_bet,
                    "bet_rating": analysis.bet_rating,
                    "data_quality": analysis.data_quality,
                    "actual_result": analysis.actual_result,
                    "actual_score": analysis.actual_score,
                    "ev_realized": analysis.ev_realized,
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                }

        except Exception as e:
            logger.error(f"Error retrieving analysis: {e}")
            return None

    def list_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with self._session() as session:
                analyses = session.query(Analysis).order_by(
                    Analysis.created_at.desc()
                ).limit(limit).all()

                return [
                    {
                        "analysis_id": a.analysis_id,
                        "match_id": a.match_id,
                        "home_team": a.home_team,
                        "away_team": a.away_team,
                        "competition": a.competition,
                        "confidence": a.confidence,
                        "ev": a.ev,
                        "bet_rating": a.bet_rating,
                        "data_quality": a.data_quality,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in analyses
                ]

        except Exception as e:
            logger.error(f"Error listing analyses: {e}")
            return []

    def update_result(
        self,
        analysis_id: str,
        actual_result: str,
        actual_score: str,
        ev_realized: Optional[float] = None,
    ) -> bool:
        try:
            with self._session() as session:
                analysis = session.query(Analysis).filter(
                    Analysis.analysis_id == analysis_id
                ).first()

                if not analysis:
                    logger.warning(f"Analysis not found: {analysis_id}")
                    return False

                analysis.actual_result = actual_result
                analysis.actual_score = actual_score
                if ev_realized is not None:
                    analysis.ev_realized = ev_realized
                analysis.updated_at = datetime.now()

            logger.info(f"Result updated for analysis: {analysis_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating result: {e}")
            return False

    def get_analyses_by_match(self, match_id: str) -> List[Dict[str, Any]]:
        try:
            with self._session() as session:
                analyses = session.query(Analysis).filter(
                    Analysis.match_id == match_id
                ).all()

                return [
                    {
                        "analysis_id": a.analysis_id,
                        "confidence": a.confidence,
                        "ev": a.ev,
                        "bet_rating": a.bet_rating,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in analyses
                ]

        except Exception as e:
            logger.error(f"Error getting analyses by match: {e}")
            return []


_repository = None


def get_repository(database_url: str = "sqlite:///data/db/goalcast.db") -> Repository:
    global _repository
    if _repository is None:
        _repository = Repository(database_url)
    return _repository
