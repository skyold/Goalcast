#!/usr/bin/env python3

import sys
import json
import argparse
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.aggregator.match_builder import MatchBuilder
from src.aggregator.manual_input import parse_lineup, parse_injuries, parse_odds
from src.engine.prompt import PromptBuilder
from src.engine.runner import AnalysisRunner
from src.engine.parser import OutputParser
from src.storage.repository import get_repository
from src.utils.formatter import OutputFormatter
from src.utils.logger import logger


def parse_args():
    parser = argparse.ArgumentParser(description="Goalcast AI - Football Match Analysis")
    parser.add_argument("--match_id", required=True, help="FootyStats match ID")
    parser.add_argument("--lineup_home", help="Home team lineup (JSON or text)")
    parser.add_argument("--lineup_away", help="Away team lineup (JSON or text)")
    parser.add_argument("--injuries_home", help="Home team injuries (JSON or text)")
    parser.add_argument("--injuries_away", help="Away team injuries (JSON or text)")
    parser.add_argument("--odds", help="Manual odds (format: home@2.10 draw@3.40 away@3.20)")
    parser.add_argument("--dry_run", action="store_true", help="Generate input only, no Claude call")
    parser.add_argument("--no_cache", action="store_true", help="Ignore cached data")
    parser.add_argument("--output", help="Output file path (JSON)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    return parser.parse_args()


def parse_manual_override(value: str):
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass

    return value


async def run_analysis(args):
    manual_overrides = {}

    if args.lineup_home:
        override_val = parse_manual_override(args.lineup_home)
        if isinstance(override_val, str):
            manual_overrides["lineup_home"] = parse_lineup(override_val)
        else:
            manual_overrides["lineup_home"] = override_val

    if args.lineup_away:
        override_val = parse_manual_override(args.lineup_away)
        if isinstance(override_val, str):
            manual_overrides["lineup_away"] = parse_lineup(override_val)
        else:
            manual_overrides["lineup_away"] = override_val

    if args.injuries_home:
        override_val = parse_manual_override(args.injuries_home)
        if isinstance(override_val, str):
            manual_overrides["injuries_home"] = parse_injuries(override_val)
        else:
            manual_overrides["injuries_home"] = override_val

    if args.injuries_away:
        override_val = parse_manual_override(args.injuries_away)
        if isinstance(override_val, str):
            manual_overrides["injuries_away"] = parse_injuries(override_val)
        else:
            manual_overrides["injuries_away"] = override_val

    if args.odds:
        manual_overrides["odds"] = parse_odds(args.odds)

    logger.info("Building analysis input...")
    builder = MatchBuilder()

    analysis_input = await builder.build(args.match_id, manual_overrides)

    if not analysis_input:
        logger.error("Failed to build analysis input")
        print("❌ Error: Failed to fetch match data. Check the match_id and API configuration.")
        return None

    input_dict = analysis_input.model_dump()
    print(f"\n✅ Data collection complete")
    print(f"   Home: {analysis_input.match_info.home_team}")
    print(f"   Away: {analysis_input.match_info.away_team}")
    print(f"   Competition: {analysis_input.match_info.competition}")
    print(f"   Data Quality: {analysis_input.match_info.data_quality.value}")
    if analysis_input.match_info.missing_data:
        print(f"   Missing: {', '.join(analysis_input.match_info.missing_data)}")

    if args.dry_run:
        print("\n📋 DRY RUN - Input JSON:")
        print(json.dumps(input_dict, indent=2, ensure_ascii=False, default=str))
        print("\n✅ Dry run complete. No Claude API call made.")
        return None

    logger.info("Building prompt...")
    prompt_builder = PromptBuilder()
    prompt = prompt_builder.build(analysis_input)

    logger.info("Calling Claude API...")
    print("\n🤖 Analyzing with Claude AI...")
    runner = AnalysisRunner()
    response = await runner.run(prompt)

    if not response:
        logger.error("Claude API call failed")
        print("❌ Error: Claude API call failed. Check API key and try again.")
        return None

    logger.info("Parsing output...")
    parser = OutputParser()
    output = parser.parse(response)

    if not output:
        logger.error("Output parsing failed")
        print("❌ Error: Failed to parse Claude response.")
        output_dict = {
            "match_info": input_dict.get("match_info", {}),
            "raw_response": response[:500] if response and len(response) > 500 else response,
            "error": "Parsing failed"
        }
    else:
        output_dict = output.model_dump()

    return analysis_input, output, output_dict


def main():
    args = parse_args()

    logger.info(f"Starting analysis for match_id={args.match_id}")

    result = asyncio.run(run_analysis(args))

    if result is None:
        sys.exit(1)

    analysis_input, output, output_dict = result

    print(OutputFormatter.format_terminal(output_dict))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_match_id = args.match_id.replace("/", "_")
    default_output = f"data/exports/{safe_match_id}_{timestamp}.json"
    output_path = Path(args.output) if args.output else Path(default_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_dict, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Results saved to: {output_path}")

    if output:
        try:
            repo = get_repository()
            analysis_id = repo.save_analysis(
                match_id=analysis_input.match_info.match_id,
                home_team=analysis_input.match_info.home_team,
                away_team=analysis_input.match_info.away_team,
                competition=analysis_input.match_info.competition,
                prompt_version="v3.0",
                input_data=analysis_input.model_dump(),
                output_data=output_dict,
                confidence=output.decision.confidence,
                ev=output.decision.ev,
                risk_adjusted_ev=output.decision.risk_adjusted_ev,
                best_bet=output.decision.best_bet,
                bet_rating=output.decision.bet_rating.value,
                data_quality=output.match_info.data_quality.value,
            )

            if analysis_id:
                print(f"✅ Analysis saved to database: {analysis_id}")
            else:
                print("⚠️  Warning: Failed to save to database")

        except Exception as e:
            logger.error(f"Database error: {e}")
            print("⚠️  Warning: Database save failed")

    print("\n✨ Analysis complete!")


if __name__ == "__main__":
    main()
