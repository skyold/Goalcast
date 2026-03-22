import json
from datetime import datetime
from typing import Dict, Any


class OutputFormatter:
    @staticmethod
    def format_terminal(output: Dict[str, Any]) -> str:
        match_info = output.get("match_info", {})
        model = output.get("model_output", {})
        market = output.get("market", {})
        decision = output.get("decision", {})
        meta = output.get("meta", {})

        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("⚽ GOALCAST AI — ANALYSIS RESULT")
        lines.append("=" * 60)

        lines.append(f"\n📋 Match: {match_info.get('home_team', '?')} vs {match_info.get('away_team', '?')}")
        lines.append(f"🏆 Competition: {match_info.get('competition', 'Unknown')}")
        lines.append(f"📊 Match Type: {match_info.get('match_type', 'A')}")
        lines.append(f"🔍 Data Quality: {match_info.get('data_quality', 'medium').upper()}")

        probs = model.get("final_probabilities", {})
        lines.append(f"\n📈 MODEL PROBABILITIES:")
        lines.append(f"   Home Win: {probs.get('home_win', '0%')}")
        lines.append(f"   Draw:     {probs.get('draw', '0%')}")
        lines.append(f"   Away Win: {probs.get('away_win', '0%')}")

        top_scores = model.get("top_scores", [])
        if top_scores:
            lines.append(f"\n🎯 TOP SCORES:")
            for score_item in top_scores[:5]:
                lines.append(f"   {score_item.get('score', '?')}: {score_item.get('probability', '0%')}")

        market_probs = market.get("market_probabilities", {})
        if market_probs:
            lines.append(f"\n📉 MARKET PROBABILITIES:")
            lines.append(f"   Home Win: {market_probs.get('home_win', '0%')}")
            lines.append(f"   Draw:     {market_probs.get('draw', '0%')}")
            lines.append(f"   Away Win: {market_probs.get('away_win', '0%')}")

            divergence = market.get("divergence", {})
            if divergence:
                lines.append(f"\n📊 DIVERGENCE (Model - Market):")
                for key, val in divergence.items():
                    sign = "+" if val > 0 else ""
                    lines.append(f"   {key}: {sign}{val:.1f}%")

            lines.append(f"\n💡 Market Signal: {market.get('signal_direction', '中立')} ({market.get('signal_strength', '弱')})")

        lines.append(f"\n💰 DECISION:")
        lines.append(f"   EV: {decision.get('ev', 0):.3f}")
        lines.append(f"   Risk-Adjusted EV: {decision.get('risk_adjusted_ev', 0):.3f}")
        lines.append(f"   Best Bet: {decision.get('best_bet', 'N/A')}")
        lines.append(f"   Rating: {decision.get('bet_rating', '不推荐')}")
        lines.append(f"   Confidence: {decision.get('confidence', 0)}")

        confidence = decision.get("confidence", 50)
        if confidence >= 80:
            conf_bar = "🟢🟢🟢🟢🟢"
        elif confidence >= 70:
            conf_bar = "🟡🟡🟡🟡⚪"
        elif confidence >= 60:
            conf_bar = "🟠🟠🟠⚪⚪"
        else:
            conf_bar = "🔴🔴⚪⚪⚪"
        lines.append(f"   Confidence Bar: {conf_bar}")

        if meta.get("data_quality_notes"):
            lines.append(f"\n📝 Notes: {meta.get('data_quality_notes')}")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)

    @staticmethod
    def format_json(output: Dict[str, Any]) -> str:
        return json.dumps(output, indent=2, ensure_ascii=False)

    @staticmethod
    def format_summary(output: Dict[str, Any]) -> str:
        match_info = output.get("match_info", {})
        model = output.get("model_output", {})
        decision = output.get("decision", {})

        probs = model.get("final_probabilities", {})

        summary = (
            f"{match_info.get('home_team', '?')} vs {match_info.get('away_team', '?')} | "
            f"{probs.get('home_win', '0%')}/{probs.get('draw', '0%')}/{probs.get('away_win', '0%')} | "
            f"EV: {decision.get('ev', 0):.3f} ({decision.get('bet_rating', 'N/A')}) | "
            f"Confidence: {decision.get('confidence', 0)}"
        )

        return summary
