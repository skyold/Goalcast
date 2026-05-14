"""
Goalcast Review Engine
======================
Automated post-match review system. Fetches actual results, compares with predictions,
and updates system performance metrics.

Usage:
    PYTHONPATH=. ./.venv/bin/python scripts/review_engine.py
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Configuration ---
ROOT_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = ROOT_DIR / "data" / "predictions"
RESULTS_DIR = ROOT_DIR / "data" / "results"
DIARY_DIR = ROOT_DIR / "diary"
MEMORY_FILE = ROOT_DIR / "MEMORY.md"

def brier_score_component(probabilities: Dict[str, float], actual_result: str) -> float:
    """Calculate Brier score for a single match prediction."""
    mapping = {"home_win": "home_win", "draw": "draw", "away_win": "away_win"}
    actual_key = mapping.get(actual_result)
    
    pred = {
        "home_win": float(probabilities.get("home_win", "0").rstrip('%')) / 100,
        "draw": float(probabilities.get("draw", "0").rstrip('%')) / 100,
        "away_win": float(probabilities.get("away_win", "0").rstrip('%')) / 100,
    }
    
    outcome = {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}
    if actual_key:
        outcome[actual_key] = 1.0
        
    return sum((pred[k] - outcome[k]) ** 2 for k in pred)

async def review_matches():
    """Stub — single-source rewrite pending (Task 9)."""
    # 2026-05-14 pivot: FootyStatsProvider removed — needs rewrite for OddAlerts.
    raise NotImplementedError("Provider removed — see 2026-05-14 pivot")

def generate_match_markdown(result: Dict, output_path: Path):
    """Generate a human-readable Markdown report for a single match result."""
    mi = result["match_info"]
    ao = result["actual_outcome"]
    acc = result["accuracy"]
    
    status_icon = "✅" if acc["correct_result"] else "❌"
    
    content = f"""# Match Review: {mi['home_team']} vs {mi['away_team']}

## 1. 核心结论 (Core Conclusion)
- **比赛结果**: {mi['final_score']} ({ao['result']})
- **预测表现**: {status_icon} {"命中" if acc["correct_result"] else "未命中"}
- **比分对位**: {"比分完全命中！" if acc["top_score_hit"] else "比分未命中"}
- **Brier 均值**: {acc['brier_avg']:.4f}

## 2. 详细预测对比 (Prediction Comparison)

| 模型 | 最佳投注 | 预测比分 | 置信度 | 实际结果 | 状态 |
| :--- | :--- | :--- | :--- | :--- | :--- |
"""
    for p in result["predictions_reviewed"]:
        hit_icon = "✓" if p["correct_result"] else "✗"
        content += f"| {p['method']} | {p['predicted_best_bet']} | {p['predicted_top_score']} | {p['confidence']} | {mi['final_score']} | {hit_icon} |\n"

    content += f"""
## 3. 复盘建议 (Strategy Suggestions)
- **模型反馈**: {result.get('lesson', '暂无特定模型改进建议。')}
- **数据质量**: 鉴于本场比赛结果与预测的偏差，建议检查在该联赛或特定赔率区间下的模型权重分配。
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

def update_diary(date: str, home: str, away: str, score: str, reviews: List[Dict]):
    diary_file = DIARY_DIR / f"{date}.md"
    
    header = f"# Daily Review — {date}\n\n"
    table_header = "| Match | Predicted | Actual | Correct? | Method |\n|-------|-----------|--------|----------|--------|\n"
    
    rows = ""
    for r in reviews:
        hit_icon = "✓" if r["correct_result"] else "✗"
        rows += f"| {home} vs {away} | {r['predicted_best_bet']} | {score} | {hit_icon} | {r['method']} |\n"
        
    if not diary_file.exists():
        content = header + "## Matches Reviewed\n\n" + table_header + rows
    else:
        with open(diary_file, 'r', encoding='utf-8') as f:
            content = f.read()
        if table_header not in content:
            # Re-build if missing sections
            content = header + "## Matches Reviewed\n\n" + table_header + rows
        else:
            # Append to table
            lines = content.splitlines()
            last_table_line = -1
            for i, line in enumerate(lines):
                if line.startswith("|"):
                    last_table_line = i
            if last_table_line != -1:
                lines.insert(last_table_line + 1, rows.strip())
                content = "\n".join(lines)
            else:
                content += "\n" + table_header + rows
            
    with open(diary_file, 'w', encoding='utf-8') as f:
        f.write(content)

def update_memory():
    # Load all results to calculate cumulative stats
    if not RESULTS_DIR.exists():
        return
        
    all_results = sorted(RESULTS_DIR.glob("*.json"))
    total_preds = 0
    total_correct = 0
    brier_scores = []
    
    for rf in all_results:
        with open(rf, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for p in data.get("predictions_reviewed", []):
                total_preds += 1
                if p.get("correct_result"):
                    total_correct += 1
                if "brier_component" in p:
                    brier_scores.append(p["brier_component"])
                    
    hit_rate = (total_correct / total_preds * 100) if total_preds > 0 else 0.0
    avg_brier = (sum(brier_scores) / len(brier_scores)) if brier_scores else 0.0
    
    memory_content = f"""# Goalcast Project Memory
Last Updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Cumulative Performance
- Total Predictions: {total_preds}
- Correct Result Hits: {total_correct}
- Hit Rate: {hit_rate:.1f}%
- Average Brier Score: {avg_brier:.4f}

## Recent Reviews
"""
    # Add last 10 reviews
    for rf in all_results[-10:]:
        with open(rf, 'r', encoding='utf-8') as f:
            data = json.load(f)
            mi = data.get("match_info", {})
            ao = data.get("actual_outcome", {})
            memory_content += f"- {mi.get('date')}: {mi.get('home_team')} {ao.get('home_goals')}-{ao.get('away_goals')} {mi.get('away_team')}\n"

    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        f.write(memory_content)

if __name__ == "__main__":
    asyncio.run(review_matches())
