"""
将旧格式 MC-*.json 文件迁移到新统一格式。
旧格式有 orchestrator/analysis/trading/review/state 等字段，
新格式只保留 metadata/raw_data/analysis。

用法：
    cd backend && python scripts/migrate_matches.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "matches"


def _migrate_record(record: dict) -> dict | None:
    """将旧格式 record 转为新格式。返回 None 表示已是新格式或无法迁移。"""
    if "metadata" in record and "provider_ids" in record.get("metadata", {}):
        return None  # 已是新格式

    orch = record.get("orchestrator", {}) or {}
    meta_old = record.get("metadata", {}) or {}

    home_team = orch.get("home_team") or meta_old.get("home_team", "")
    away_team = orch.get("away_team") or meta_old.get("away_team", "")
    league_raw = orch.get("league") or meta_old.get("league", "")
    league = league_raw.get("name", "") if isinstance(league_raw, dict) else str(league_raw or "")
    kickoff = orch.get("kickoff_time") or meta_old.get("kickoff_time", "")
    sm_id = orch.get("fixture_id") or meta_old.get("fixture_id")
    oa_id = meta_old.get("oa_fixture_id")

    provider_ids: dict = {}
    if sm_id:
        provider_ids["sportmonks"] = sm_id
    if oa_id:
        provider_ids["oddalerts"] = oa_id

    old_status = record.get("status", "unknown")
    new_status_map = {
        "pending": "pending",
        "analyzing": "pending",
        "analyzed": "collected",
        "trading": "collected",
        "traded": "collected",
        "reviewing": "collected",
        "reviewed": "collected",
        "reported": "analyzed",
        "feedback": "collected",
        "aborted": "error",
        "abandoned": "error",
        "error": "error",
    }
    new_status = new_status_map.get(old_status, "pending")

    analysis_old = record.get("analysis", {}) or {}
    trading_old = record.get("trading", {}) or {}
    analysis_new: dict = {}
    if isinstance(analysis_old, dict) and analysis_old:
        v4 = analysis_old.get("v4.0", {})
        src = v4 if isinstance(v4, dict) and v4.get("home_xg") else analysis_old
        analysis_new = {
            "home_xg": src.get("home_xg"),
            "away_xg": src.get("away_xg"),
            "ah_recommendation": src.get("ah_recommendation"),
            "confidence": src.get("confidence"),
        }
        if isinstance(trading_old, dict) and trading_old:
            results = trading_old.get("results", {})
            if isinstance(results, dict):
                analysis_new["kelly_fraction"] = results.get("kelly_fraction")

    raw_data = record.get("raw_data", {}) or {}

    return {
        "match_id": record["match_id"],
        "status": new_status,
        "metadata": {
            "match_id": record["match_id"],
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "kickoff_time": kickoff,
            "provider_ids": provider_ids,
            "collected_at": orch.get("prepared_at") or meta_old.get("prepared_at"),
        },
        "raw_data": raw_data,
        "analysis": analysis_new,
    }


def main():
    parser = argparse.ArgumentParser(description="迁移旧格式 match 文件到新格式")
    parser.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    args = parser.parse_args()

    if not DATA_DIR.exists():
        print(f"目录不存在: {DATA_DIR}")
        sys.exit(0)

    files = list(DATA_DIR.glob("MC-*.json"))
    migrated = 0
    skipped = 0
    errors = 0

    for fp in files:
        try:
            record = json.loads(fp.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] 读取失败 {fp.name}: {e}")
            errors += 1
            continue

        new_record = _migrate_record(record)
        if new_record is None:
            skipped += 1
            continue

        if args.dry_run:
            print(f"[DRY] 会迁移: {fp.name} (status: {record.get('status')} → {new_record['status']})")
        else:
            fp.write_text(json.dumps(new_record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] 已迁移: {fp.name}")
        migrated += 1

    print(f"\n完成：迁移 {migrated}，跳过（已是新格式）{skipped}，错误 {errors}")


if __name__ == "__main__":
    main()
