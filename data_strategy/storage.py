"""
分析结果存储层

持久化分析结果到：
1. data/reports/YYYY-MM-DD/Match_Name_provider_model.json（供其他 agent 读取）
2. data/analysis.db SQLite（供回测和历史查询）
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from config.settings import BASE_DIR


class AnalysisStorage:

    def __init__(
        self,
        db_path: Optional[Path] = None,
        reports_dir: Optional[Path] = None,
    ) -> None:
        self.db_path = db_path or (BASE_DIR / "data" / "analysis.db")
        self.reports_dir = reports_dir or (BASE_DIR / "data" / "reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def init(self) -> None:
        """Create tables if not exist (idempotent)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    competition TEXT NOT NULL,
                    data_provider TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    home_win_prob REAL,
                    draw_prob REAL,
                    away_win_prob REAL,
                    confidence INTEGER,
                    best_bet TEXT,
                    ev_adjusted REAL,
                    result_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS match_results (
                    match_date TEXT NOT NULL,
                    home_team TEXT NOT NULL,
                    away_team TEXT NOT NULL,
                    home_goals INTEGER,
                    away_goals INTEGER,
                    PRIMARY KEY (match_date, home_team, away_team)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_analyses_date
                ON analyses (match_date, home_team, away_team)
            """)
            conn.commit()

    def save_analysis(
        self,
        match_date: str,
        home_team: str,
        away_team: str,
        competition: str,
        data_provider: str,
        model_version: str,
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        confidence: int,
        best_bet: str,
        ev_adjusted: float,
        result_json: Any,
    ) -> int:
        """Save analysis to SQLite and write JSON report. Returns row id."""
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result_str = json.dumps(result_json, ensure_ascii=False)

        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                """INSERT INTO analyses
                   (match_date, home_team, away_team, competition,
                    data_provider, model_version, home_win_prob, draw_prob, away_win_prob,
                    confidence, best_bet, ev_adjusted, result_json, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (match_date, home_team, away_team, competition,
                 data_provider, model_version, home_win_prob, draw_prob, away_win_prob,
                 confidence, best_bet, ev_adjusted, result_str, created_at),
            )
            conn.commit()
            row_id = cur.lastrowid

        # Write JSON report
        date_dir = self.reports_dir / match_date
        date_dir.mkdir(parents=True, exist_ok=True)
        model_slug = model_version.replace(".", "")
        fname = f"{home_team}_vs_{away_team}_{data_provider}_{model_slug}.json"
        report_path = date_dir / fname
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)

        return row_id
