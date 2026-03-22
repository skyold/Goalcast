import json
import re
from typing import Optional, Dict, Any
from pathlib import Path

from src.aggregator.schema import (
    AnalysisOutput,
    MatchInfo,
    ModelOutput,
    MarketData,
    DecisionData,
    ReasoningChain,
    MetaData,
    DataQualityLevel,
    BetRating,
    SignalDirection,
    SignalStrength,
)
from src.utils.logger import logger
from config.settings import settings


class OutputParser:
    def __init__(self, failed_output_dir: Optional[Path] = None):
        self.failed_dir = failed_output_dir or Path("data/exports/failed")
        self.failed_dir.mkdir(parents=True, exist_ok=True)

    def parse(self, raw_response: str) -> Optional[AnalysisOutput]:
        logger.info("Parsing Claude response")

        json_str = self._extract_json(raw_response)
        if not json_str:
            logger.error("No JSON found in response")
            self._save_failed_output(raw_response, "no_json")
            return None

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            self._save_failed_output(raw_response, "parse_error")
            return None

        validated = self._validate_and_fix(data)
        if not validated:
            logger.error("Validation failed")
            self._save_failed_output(raw_response, "validation_failed")
            return None

        try:
            output = self._build_output(validated)
            logger.info("Output parsed successfully")
            return output
        except Exception as e:
            logger.error(f"Error building output: {e}")
            self._save_failed_output(raw_response, "build_error")
            return None

    def _extract_json(self, text: str) -> Optional[str]:
        text = text.strip()

        code_block_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        matches = re.findall(code_block_pattern, text)
        if matches:
            return matches[0].strip()

        json_pattern = r"\{[\s\S]*\}"
        matches = re.findall(json_pattern, text)
        if matches:
            return matches[0].strip()

        if text.startswith("{") and text.endswith("}"):
            return text

        return None

    def _validate_and_fix(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not isinstance(data, dict):
            return None

        if "match_info" not in data:
            logger.warning("Missing match_info, adding empty structure")
            data["match_info"] = {}

        if "model_output" not in data:
            data["model_output"] = {}
        if "final_probabilities" not in data["model_output"]:
            data["model_output"]["final_probabilities"] = {
                "home_win": "33%",
                "draw": "33%",
                "away_win": "34%",
            }
        if "base_xg" not in data["model_output"]:
            data["model_output"]["base_xg"] = {"home": 0.0, "away": 0.0}
        if "adjusted_xg" not in data["model_output"]:
            data["model_output"]["adjusted_xg"] = {"home": 0.0, "away": 0.0}
        if "top_scores" not in data["model_output"]:
            data["model_output"]["top_scores"] = []

        if "market" not in data:
            data["market"] = {}
        if "market_probabilities" not in data["market"]:
            data["market"]["market_probabilities"] = {
                "home_win": "33%",
                "draw": "33%",
                "away_win": "34%",
            }
        if "divergence" not in data["market"]:
            data["market"]["divergence"] = {
                "home_win": 0.0,
                "draw": 0.0,
                "away_win": 0.0,
            }
        if "signal_direction" not in data["market"]:
            data["market"]["signal_direction"] = "中立"
        if "signal_strength" not in data["market"]:
            data["market"]["signal_strength"] = "弱"

        if "decision" not in data:
            data["decision"] = {}
        if "ev" not in data["decision"]:
            data["decision"]["ev"] = 0.0
        if "risk_adjusted_ev" not in data["decision"]:
            data["decision"]["risk_adjusted_ev"] = 0.0
        if "best_bet" not in data["decision"]:
            data["decision"]["best_bet"] = ""
        if "bet_rating" not in data["decision"]:
            data["decision"]["bet_rating"] = "不推荐"
        if "confidence" not in data["decision"]:
            data["decision"]["confidence"] = 50

        if "reasoning_chain" not in data:
            data["reasoning_chain"] = {}
        for field in [
            "layer1_summary",
            "layer2_adjustments",
            "layer3_signal",
            "layer4_tempo",
            "layer5_top_score_logic",
            "layer6_bayesian_update",
            "layer7_ev_calc",
            "layer8_confidence_breakdown",
        ]:
            if field not in data["reasoning_chain"]:
                data["reasoning_chain"][field] = ""

        if "meta" not in data:
            data["meta"] = {}
        for field in [
            "match_type_classification",
            "league_params_used",
            "data_quality_notes",
        ]:
            if field not in data["meta"]:
                data["meta"][field] = ""

        probabilities = data["model_output"]["final_probabilities"]
        prob_values = []
        for key in ["home_win", "draw", "away_win"]:
            prob_str = probabilities.get(key, "0%").replace("%", "")
            try:
                prob_values.append(float(prob_str))
            except ValueError:
                prob_values.append(0.0)

        total = sum(prob_values)
        if total < 99 or total > 101:
            logger.warning(f"Probabilities sum to {total}, normalizing")
            if total > 0:
                factor = 100.0 / total
                for i, key in enumerate(["home_win", "draw", "away_win"]):
                    prob_values[i] *= factor
                    probabilities[key] = f"{prob_values[i]:.1f}%"

        confidence = data["decision"].get("confidence", 50)
        confidence = max(settings.CONFIDENCE_MIN, min(settings.CONFIDENCE_MAX, confidence))
        data["decision"]["confidence"] = confidence

        ev = data["decision"].get("ev", 0)
        ev = max(-1.0, min(2.0, ev))
        data["decision"]["ev"] = ev

        return data

    def _build_output(self, data: Dict[str, Any]) -> AnalysisOutput:
        match_info_data = data.get("match_info", {})

        match_info = MatchInfo(
            match_id=match_info_data.get("match_id", ""),
            home_team=match_info_data.get("home_team", ""),
            away_team=match_info_data.get("away_team", ""),
            competition=match_info_data.get("competition", ""),
            match_type=match_info_data.get("match_type", "A"),
            data_quality=DataQualityLevel(match_info_data.get("data_quality", "medium")),
            missing_data=match_info_data.get("missing_data", []),
        )

        model_output_data = data.get("model_output", {})
        model_output = ModelOutput(
            base_xg=model_output_data.get("base_xg", {"home": 0.0, "away": 0.0}),
            adjusted_xg=model_output_data.get("adjusted_xg", {"home": 0.0, "away": 0.0}),
            final_probabilities=model_output_data.get(
                "final_probabilities",
                {"home_win": "0%", "draw": "0%", "away_win": "0%"},
            ),
            top_scores=model_output_data.get("top_scores", []),
        )

        market_data = data.get("market", {})
        market = MarketData(
            market_probabilities=market_data.get(
                "market_probabilities",
                {"home_win": "0%", "draw": "0%", "away_win": "0%"},
            ),
            divergence=market_data.get("divergence", {"home_win": 0.0, "draw": 0.0, "away_win": 0.0}),
            signal_direction=SignalDirection(market_data.get("signal_direction", "中立")),
            signal_strength=SignalStrength(market_data.get("signal_strength", "弱")),
        )

        decision_data = data.get("decision", {})
        decision = DecisionData(
            ev=decision_data.get("ev", 0.0),
            risk_adjusted_ev=decision_data.get("risk_adjusted_ev", 0.0),
            best_bet=decision_data.get("best_bet", ""),
            bet_rating=BetRating(decision_data.get("bet_rating", "不推荐")),
            confidence=decision_data.get("confidence", 50),
        )

        reasoning_data = data.get("reasoning_chain", {})
        layer2 = reasoning_data.get("layer2_adjustments", [])
        if isinstance(layer2, str):
            layer2 = [layer2]
        reasoning = ReasoningChain(
            layer1_summary=reasoning_data.get("layer1_summary", ""),
            layer2_adjustments=layer2,
            layer3_signal=reasoning_data.get("layer3_signal", ""),
            layer4_tempo=reasoning_data.get("layer4_tempo", ""),
            layer5_top_score_logic=reasoning_data.get("layer5_top_score_logic", ""),
            layer6_bayesian_update=reasoning_data.get("layer6_bayesian_update", ""),
            layer7_ev_calc=reasoning_data.get("layer7_ev_calc", ""),
            layer8_confidence_breakdown=reasoning_data.get("layer8_confidence_breakdown", ""),
        )

        meta_data = data.get("meta", {})
        meta = MetaData(
            match_type_classification=meta_data.get("match_type_classification", ""),
            league_params_used=meta_data.get("league_params_used", ""),
            data_quality_notes=meta_data.get("data_quality_notes", ""),
        )

        return AnalysisOutput(
            match_info=match_info,
            model_output=model_output,
            market=market,
            decision=decision,
            reasoning_chain=reasoning,
            meta=meta,
        )

    def _save_failed_output(self, raw_response: str, error_type: str):
        from datetime import datetime
        import hashlib

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_suffix = hashlib.md5(raw_response[:100].encode()).hexdigest()[:8]
        filename = f"failed_{error_type}_{timestamp}_{hash_suffix}.txt"

        try:
            with open(self.failed_dir / filename, "w") as f:
                f.write(raw_response)
            logger.info(f"Failed output saved to {filename}")
        except IOError as e:
            logger.error(f"Failed to save failed output: {e}")
