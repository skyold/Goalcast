"""
Goalcast Backtest Engine
========================
Batch evaluation of historical predictions against actual match results.
Calculates Brier Score, Log Loss, ROI, Hit Rate, and Sharpe Ratio.

Usage:
    python -m scripts.backtest_engine --start 2026-04-01 --end 2026-04-30
    python -m scripts.backtest_engine --date 2026-04-09
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ─── Configuration ─────────────────────────────────────────────────────
GOALCAST_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = GOALCAST_ROOT / "data" / "predictions"
RESULTS_DIR = GOALCAST_ROOT / "data" / "results"
BACKTESTS_DIR = GOALCAST_ROOT / "data" / "backtests"
UNIT_STAKE = 1.0  # Flat stake unit for ROI calculation
EV_THRESHOLD = 0.05  # Only bet when risk-adjusted EV > this


# ─── Metrics ───────────────────────────────────────────────────────────

def brier_score(probabilities: Dict[str, float], actual_result: str) -> float:
    """
    Brier Score = (1/N) * Σ(p_i - o_i)²
    Lower is better.
    """
    mapping = {"home_win": "home", "draw": "draw", "away_win": "away"}
    actual_key = mapping.get(actual_result, actual_result)

    pred = {
        "home": probabilities.get("home_win", 0) / 100,
        "draw": probabilities.get("draw", 0) / 100,
        "away": probabilities.get("away_win", 0) / 100,
    }
    outcome = {"home": 0.0, "draw": 0.0, "away": 0.0}
    outcome[actual_key] = 1.0

    return sum((pred[k] - outcome[k]) ** 2 for k in pred)


def log_loss(probabilities: Dict[str, float], actual_result: str, epsilon: float = 1e-15) -> float:
    """
    Log Loss = -Σ[o_i * log(p_i)]
    Lower is better.
    """
    mapping = {"home_win": "home", "draw": "draw", "away_win": "away"}
    actual_key = mapping.get(actual_result, actual_result)

    prob = {
        "home": probabilities.get("home_win", 0) / 100,
        "draw": probabilities.get("draw", 0) / 100,
        "away": probabilities.get("away_win", 0) / 100,
    }

    p = max(min(prob[actual_key], 1 - epsilon), epsilon)
    return -math.log(p)


def calculate_roi(
    predictions: List[Dict],
    results: Dict[str, str],
    ev_threshold: float = EV_THRESHOLD,
    unit_stake: float = UNIT_STAKE,
) -> Tuple[float, float, float]:
    """
    Calculate ROI based on predictions with positive EV.
    Returns (total_profit, total_staked, roi_pct).
    """
    total_profit = 0.0
    total_staked = 0.0

    for pred in predictions:
        match_key = f"{pred['match_info']['home_team']}_{pred['match_info']['away_team']}"
        if match_key not in results:
            continue

        ev = pred.get("decision", {}).get("risk_adjusted_ev", pred.get("decision", {}).get("ev", 0))
        if ev <= ev_threshold:
            continue  # Skip bets that don't meet EV threshold

        best_bet = pred.get("decision", {}).get("best_bet", "不推荐")
        if best_bet == "不推荐":
            continue

        # Map best_bet to actual result key
        bet_to_result = {"主胜": "home_win", "平": "draw", "客胜": "away_win"}
        result_key = bet_to_result.get(best_bet)
        if not result_key:
            continue

        actual_result = results[match_key]
        won = (result_key == actual_result)

        # Get odds from market probabilities
        market_probs = pred.get("market", {}).get("market_probabilities", {})
        implied_prob = market_probs.get(result_key, 50) / 100
        if implied_prob <= 0:
            continue
        odds = 1.0 / implied_prob

        total_staked += unit_stake
        if won:
            total_profit += unit_stake * (odds - 1)
        else:
            total_profit -= unit_stake

    roi_pct = (total_profit / total_staked * 100) if total_staked > 0 else 0.0
    return total_profit, total_staked, roi_pct


def hit_rate(predictions: List[Dict], results: Dict[str, str]) -> Tuple[int, int, float]:
    """
    Calculate direction hit rate.
    """
    correct = 0
    total = 0

    for pred in predictions:
        match_key = f"{pred['match_info']['home_team']}_{pred['match_info']['away_team']}"
        if match_key not in results:
            continue
        total += 1

        probs = pred.get("probabilities", {})
        predicted = max(probs, key=probs.get)
        actual = results[match_key]

        if predicted == actual:
            correct += 1

    return correct, total, (correct / total * 100) if total > 0 else 0.0


# ─── Data Loading ──────────────────────────────────────────────────────

def load_predictions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    method: Optional[str] = None,
) -> List[Dict]:
    """Load prediction JSON files matching date range and method."""
    if not PREDICTIONS_DIR.exists():
        return []

    predictions = []
    for f in sorted(PREDICTIONS_DIR.glob("*.json")):
        # Parse date from filename: YYYY-MM-DD_home_away_method.json
        try:
            date_str = f.stem.split("_")[0]
        except IndexError:
            continue

        if start_date and date_str < start_date:
            continue
        if end_date and date_str > end_date:
            continue
        if method and method not in f.stem:
            continue

        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                predictions.append(data)
        except (json.JSONDecodeError, IOError):
            continue

    return predictions


def load_results() -> Dict[str, str]:
    """Load actual results from data/results/. Returns {home_away: result_key}."""
    if not RESULTS_DIR.exists():
        return {}

    results = {}
    for f in sorted(RESULTS_DIR.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                actual = data.get("actual_outcome", {})
                result = actual.get("result", "")
                home = data.get("match_info", {}).get("home_team", "")
                away = data.get("match_info", {}).get("away_team", "")
                key = f"{home}_{away}"
                if result:
                    results[key] = result
        except (json.JSONDecodeError, IOError, KeyError):
            continue

    return results


# ─── Report Generation ────────────────────────────────────────────────

def generate_report(
    predictions: List[Dict],
    results: Dict[str, str],
    start_date: str,
    end_date: str,
) -> Dict:
    """Generate comprehensive backtest report."""
    # Flatten comparison reports into individual method predictions
    flattened_preds = []
    for p in predictions:
        if "comparison" in p:
            # This is a comparison report
            for method_name, result in p["comparison"].items():
                pred_copy = result.copy()
                # Ensure match info is available in the flattened version
                if "match_info" not in pred_copy:
                    pred_copy["match_info"] = {
                        "home_team": p.get("home_team", ""),
                        "away_team": p.get("away_team", ""),
                        "competition": p.get("competition", ""),
                        "date": p.get("date", "")
                    }
                flattened_preds.append(pred_copy)
        else:
            # Single prediction report
            if "match_info" not in p:
                if "home_team" in p:
                    p["match_info"] = {
                        "home_team": p.get("home_team", ""),
                        "away_team": p.get("away_team", ""),
                        "competition": p.get("competition", ""),
                        "date": p.get("date", "")
                    }
                else:
                    # Skip invalid prediction objects that have neither match_info nor home_team
                    continue
            flattened_preds.append(p)

    total = len(flattened_preds)
    matched = 0
    valid_preds = []
    for p in flattened_preds:
        if "match_info" in p and "home_team" in p["match_info"] and "away_team" in p["match_info"]:
            match_key = f"{p['match_info']['home_team']}_{p['match_info']['away_team']}"
            if match_key in results:
                matched += 1
            valid_preds.append(p)
    
    flattened_preds = valid_preds

    # Per-method metrics
    by_method = {}
    for method_name in ["v2.5", "v3.0"]:
        method_preds = [p for p in flattened_preds if p.get("method") == method_name]
        if not method_preds:
            continue

        matched_preds = [
            p for p in method_preds
            if f"{p['match_info']['home_team']}_{p['match_info']['away_team']}" in results
        ]

        brier_scores = []
        log_losses = []
        for p in matched_preds:
            match_key = f"{p['match_info']['home_team']}_{p['match_info']['away_team']}"
            actual = results.get(match_key)
            if actual:
                brier_scores.append(brier_score(p.get("probabilities", {}), actual))
                log_losses.append(log_loss(p.get("probabilities", {}), actual))

        correct, eval_total, hr = hit_rate(method_preds, results)
        profit, staked, roi = calculate_roi(method_preds, results)

        by_method[method_name] = {
            "total_predictions": len(method_preds),
            "matched_results": len(matched_preds),
            "brier_score": round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None,
            "log_loss": round(sum(log_losses) / len(log_losses), 4) if log_losses else None,
            "hit_rate_pct": round(hr, 1),
            "total_profit": round(profit, 2),
            "total_staked": round(staked, 2),
            "roi_pct": round(roi, 1),
        }

    # Overall metrics (aggregate all)
    all_brier = []
    all_logloss = []
    for p in flattened_preds:
        match_key = f"{p['match_info']['home_team']}_{p['match_info']['away_team']}"
        actual = results.get(match_key)
        if actual:
            all_brier.append(brier_score(p.get("probabilities", {}), actual))
            all_logloss.append(log_loss(p.get("probabilities", {}), actual))

    correct, eval_total, hr = hit_rate(flattened_preds, results)
    profit, staked, roi = calculate_roi(flattened_preds, results)

    report = {
        "period": {"start": start_date, "end": end_date},
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_predictions": total,
            "total_matches_evaluated": matched,
            "data_coverage": f"{(matched / total * 100):.1f}%" if total > 0 else "0%",
        },
        "metrics": {
            "brier_score": round(sum(all_brier) / len(all_brier), 4) if all_brier else None,
            "log_loss": round(sum(all_logloss) / len(all_logloss), 4) if all_logloss else None,
            "roi_pct": round(roi, 1),
            "total_profit": round(profit, 2),
            "total_staked": round(staked, 2),
            "hit_rate_pct": round(hr, 1),
        },
        "by_method": by_method,
        "optimization_notes": _generate_optimization_notes(by_method),
    }

    return report


def _generate_optimization_notes(by_method: Dict) -> str:
    """Generate actionable optimization suggestions."""
    notes = []

    if not by_method:
        return "暂无模型预测数据"

    for method, metrics in by_method.items():
        matched = metrics.get("matched_results", 0)
        
        # 只有在有足够样本量(如 >= 5)时才给出性能建议
        if matched < 5:
            notes.append(f"{method}: 样本量不足({matched})，暂不提供优化建议")
            continue

        if metrics.get("roi_pct") is not None and metrics["roi_pct"] < -5:
            notes.append(f"{method}: ROI 为 {metrics['roi_pct']}%，建议检查 EV 计算模型或调整 Kelly 系数")
        if metrics.get("hit_rate_pct") is not None and metrics["hit_rate_pct"] < 45:
            notes.append(f"{method}: 命中率 {metrics['hit_rate_pct']}% 低于随机基线，建议调整权重分配")

    if "v2.5" in by_method and "v3.0" in by_method:
        v25 = by_method["v2.5"]
        v30 = by_method["v3.0"]
        if v25.get("matched_results", 0) >= 5 and v30.get("matched_results", 0) >= 5:
            if v25.get("brier_score") and v30.get("brier_score"):
                better = "v2.5" if v25["brier_score"] < v30["brier_score"] else "v3.0"
                diff = abs(v25["brier_score"] - v30["brier_score"])
                if diff > 0.01:
                    notes.append(f"{better} 在 Brier Score 上表现更优 (差值 {diff:.4f})，建议优先使用 {better}")

    return "; ".join(notes)


def generate_markdown_report(report: Dict, output_path: str) -> str:
    """Generate human-readable Markdown report from the JSON report."""
    md_path = output_path.replace(".json", ".md")

    lines = [
        f"# Goalcast 回测评估报告 ({report['period']['start']} → {report['period']['end']})",
        f"\n**生成时间**: `{report['generated_at']}`",
        "\n## 1. 核心汇总 (Summary)",
        "| 指标 | 数值 |",
        "| :--- | :--- |",
        f"| 总预测场次 | {report['summary']['total_predictions']} |",
        f"| 已结算场次 | {report['summary']['total_matches_evaluated']} |",
        f"| 数据覆盖率 | {report['summary']['data_coverage']} |",
        f"| 平均 Brier Score | {report['metrics'].get('brier_score') or 'N/A'} |",
        f"| 平均 Log Loss | {report['metrics'].get('log_loss') or 'N/A'} |",
        f"| 整体命中率 | {report['metrics']['hit_rate_pct']}% |",
        f"| 整体 ROI | {report['metrics']['roi_pct']}% |",
        f"| 累计盈亏 | {report['metrics']['total_profit']} units |",
        "\n## 2. 模型表现对比 (By Method)",
        "| 模型版本 | 预测数 | 结算数 | 命中率 | ROI | Brier Score |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for method, m in report.get("by_method", {}).items():
        lines.append(
            f"| {method} | {m['total_predictions']} | {m['matched_results']} | "
            f"{m['hit_rate_pct']}% | {m['roi_pct']}% | {m.get('brier_score') or 'N/A'} |"
        )

    lines.extend([
        "\n## 3. 量化优化建议 (Optimization Notes)",
        f"> {report['optimization_notes']}",
        "\n---",
        "*Report generated by Goalcast Backtester*"
    ])

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return md_path


# ─── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Goalcast Backtest Engine")
    parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    parser.add_argument("--date", help="Single date (YYYY-MM-DD), shortcut for --start --end")
    parser.add_argument("--method", help="Filter by method (v2.5, v3.0)")
    parser.add_argument("--output", help="Output file path (default: auto-generated)")
    args = parser.parse_args()

    start_date = args.date or args.start or datetime.now().strftime("%Y-%m-%d")
    end_date = args.date or args.end or datetime.now().strftime("%Y-%m-%d")

    predictions = load_predictions(start_date, end_date, args.method)
    results = load_results()

    if not predictions:
        print(f"No predictions found for {start_date} to {end_date}")
        sys.exit(0)

    print(f"Loaded {len(predictions)} predictions, {len(results)} actual results")

    report = generate_report(predictions, results, start_date, end_date)

    # Output
    output_path = args.output or str(
        BACKTESTS_DIR / f"backtest_{start_date}_to_{end_date}.json"
    )
    BACKTESTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Generate human-readable Markdown report
    md_report_path = generate_markdown_report(report, output_path)

    # Print summary
    print(f"\n{'='*50}")
    print(f"  Backtest Report: {start_date} → {end_date}")
    print(f"{'='*50}")
    print(f"  Predictions: {report['summary']['total_predictions']}")
    print(f"  Matched:     {report['summary']['total_matches_evaluated']}")
    print(f"  Coverage:    {report['summary']['data_coverage']}")
    if report["metrics"].get("brier_score") is not None:
        print(f"  Brier Score: {report['metrics']['brier_score']:.4f}")
        print(f"  Log Loss:    {report['metrics']['log_loss']:.4f}")
    print(f"  Hit Rate:    {report['metrics']['hit_rate_pct']}%")
    print(f"  ROI:         {report['metrics']['roi_pct']}%")
    print(f"  Report:      {output_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
