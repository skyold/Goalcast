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
from provider.footystats.client import FootyStatsProvider

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
    provider = FootyStatsProvider()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DIARY_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load all predictions
    if not PREDICTIONS_DIR.exists():
        print("No predictions directory found.")
        return

    prediction_files = sorted(PREDICTIONS_DIR.glob("*.json"))
    if not prediction_files:
        print("No prediction files found.")
        return

    reviewed_count = 0
    
    for pred_file in prediction_files:
        try:
            with open(pred_file, 'r', encoding='utf-8') as f:
                pred_data = json.load(f)
        except Exception as e:
            print(f"Error reading {pred_file}: {e}")
            continue

        match_id = pred_data.get("match_id") or pred_data.get("id")
        if not match_id:
            print(f"No match_id or id in {pred_file}")
            continue
            
        # Extract home/away from various possible structures
        home = pred_data.get("home_team")
        away = pred_data.get("away_team")
        if not home or not away:
            # Check nested match_info (like in GCQ's newer version)
            for key in ["v2.5", "v3.0", "comparison"]:
                if key in pred_data:
                    m_info = pred_data[key].get("match_info", {})
                    if not home: home = m_info.get("home_team")
                    if not away: away = m_info.get("away_team")
        
        home = home or "Home"
        away = away or "Away"
        date_str = pred_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        # Result filename: YYYY-MM-DD_home_away.json
        safe_home = home.lower().replace(' ', '_').replace('/', '_')
        safe_away = away.lower().replace(' ', '_').replace('/', '_')
        result_file = RESULTS_DIR / f"{date_str}_{safe_home}_{safe_away}.json"
        
        if result_file.exists():
            continue
            
        print(f"Checking results for {match_id}: {home} vs {away}...")
        resp = await provider.get_match_details(match_id)
        
        if not resp or not resp.get("success"):
            print(f"Failed to fetch details for match {match_id}")
            continue
            
        match_data = resp.get("data")
        if not match_data:
            continue
            
        status = match_data.get("status")
        if status != "complete":
            print(f"Match {match_id} status: {status} (skipped)")
            continue
            
        # Match is complete, process results
        home_goals = match_data.get("homeGoalCount", 0)
        away_goals = match_data.get("awayGoalCount", 0)
        total_goals = home_goals + away_goals
        
        if home_goals > away_goals:
            actual_res = "home_win"
        elif home_goals < away_goals:
            actual_res = "away_win"
        else:
            actual_res = "draw"
            
        reviewed_predictions = []
        
        # Determine prediction source (comparison dict or top-level v2.5/v3.0)
        pred_sources = {}
        if "comparison" in pred_data:
            pred_sources = pred_data["comparison"]
        elif "v2.5" in pred_data or "v3.0" in pred_data:
            if "v2.5" in pred_data: pred_sources["v2.5"] = pred_data["v2.5"]
            if "v3.0" in pred_data: pred_sources["v3.0"] = pred_data["v3.0"]
            
        if pred_sources:
            # Flattened comparison report
            for method, p in pred_sources.items():
                probs = p.get("probabilities", {})
                best_bet = p.get("decision", {}).get("best_bet", "不推荐")
                
                # Check hit
                bet_to_res = {"主胜": "home_win", "平": "draw", "客胜": "away_win"}
                hit = (bet_to_res.get(best_bet) == actual_res)
                
                reviewed_predictions.append({
                    "method": method,
                    "predicted_home_win": probs.get("home_win"),
                    "predicted_draw": probs.get("draw"),
                    "predicted_away_win": probs.get("away_win"),
                    "predicted_best_bet": best_bet,
                    "predicted_top_score": p.get("top_scores", [{}])[0].get("score", "N/A"),
                    "confidence": p.get("decision", {}).get("confidence", 0),
                    "correct_result": hit,
                    "brier_component": brier_score_component(probs, actual_res)
                })
        else:
            # Single prediction
            probs = pred_data.get("probabilities", {})
            best_bet = pred_data.get("decision", {}).get("best_bet", "不推荐")
            bet_to_res = {"主胜": "home_win", "平": "draw", "客胜": "away_win"}
            hit = (bet_to_res.get(best_bet) == actual_res)
            
            reviewed_predictions.append({
                "method": pred_data.get("method", "v2.5"),
                "predicted_home_win": probs.get("home_win"),
                "predicted_draw": probs.get("draw"),
                "predicted_away_win": probs.get("away_win"),
                "predicted_best_bet": best_bet,
                "predicted_top_score": pred_data.get("top_scores", [{}])[0].get("score", "N/A"),
                "confidence": pred_data.get("decision", {}).get("confidence", 0),
                "correct_result": hit,
                "brier_component": brier_score_component(probs, actual_res)
            })

        # Final MatchResult
        match_result = {
            "match_info": {
                "match_id": match_id,
                "home_team": home,
                "away_team": away,
                "competition": pred_data.get("competition", "Unknown"),
                "date": date_str,
                "final_score": f"{home_goals}-{away_goals}"
            },
            "predictions_reviewed": reviewed_predictions,
            "actual_outcome": {
                "home_goals": home_goals,
                "away_goals": away_goals,
                "result": actual_res,
                "total_goals": total_goals
            },
            "accuracy": {
                "correct_result": reviewed_predictions[0]["correct_result"] if reviewed_predictions else False,
                "top_score_hit": any(p["predicted_top_score"] == f"{home_goals}-{away_goals}" for p in reviewed_predictions),
                "brier_avg": sum(p["brier_component"] for p in reviewed_predictions) / len(reviewed_predictions) if reviewed_predictions else 0.0
            },
            "lesson": pred_data.get("overall_conclusion", "") # Use original conclusion as base
        }
        
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(match_result, f, indent=2, ensure_ascii=False)
            
        # Generate companion Markdown report for the match
        md_result_file = result_file.with_suffix(".md")
        generate_match_markdown(match_result, md_result_file)
            
        print(f"Reviewed match {match_id}: Result {home_goals}-{away_goals}. Saved to {result_file} and {md_result_file}")
        reviewed_count += 1
        
        # Log to diary
        update_diary(date_str, home, away, f"{home_goals}-{away_goals}", reviewed_predictions)

    if reviewed_count > 0:
        update_memory()
        print(f"Total reviewed: {reviewed_count}. Memory and diary updated.")
    else:
        print("No new matches to review.")

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
