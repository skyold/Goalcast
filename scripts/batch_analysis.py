#!/usr/bin/env python3

import asyncio
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from provider import FootyStatsProvider, FootballDataProvider
from datasource import MatchDataSource, registry, Match
from aggregator.match_builder import MatchBuilder
from engine.prompt import PromptBuilder
from engine.runner import AnalysisRunner
from engine.parser import OutputParser
from utils.formatter import OutputFormatter
from utils.logger import logger
from config.settings import settings


class BatchAnalyzer:
    def __init__(self):
        self.footystats = FootyStatsProvider()
        self.football_data = FootballDataProvider()
        self.match_ds = MatchDataSource(providers=[self.footystats, self.football_data])
        self.builder = MatchBuilder(
            footystats_provider=self.footystats,
            football_data_provider=self.football_data,
        )
        registry.register(self.match_ds)

    async def get_upcoming_matches(
        self,
        hours: int = 72
    ) -> List[Dict[str, Any]]:
        logger.info(f"Fetching matches in next {hours} hours...")
        
        days = max(1, hours // 24 + 1)
        matches = []
        
        try:
            upcoming = await self.match_ds.fetch_upcoming("Premier League", days=days)
            if upcoming:
                for match in upcoming:
                    matches.append(match)
        except Exception as e:
            logger.warning(f"Error fetching matches: {e}")
        
        logger.info(f"Found {len(matches)} matches in next {hours} hours")
        return matches

    async def analyze_match(
        self,
        match: Match,
        dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        match_id = match.match_id
        home_team = match.home_team
        away_team = match.away_team
        
        logger.info(f"Analyzing: {home_team} vs {away_team} (ID: {match_id})")
        
        try:
            analysis_input = await self.builder.build(match_id)
            
            if not analysis_input:
                logger.warning(f"Could not build analysis for match {match_id}")
                return None
            
            prompt_builder = PromptBuilder()
            prompt = prompt_builder.build(analysis_input)
            
            if dry_run:
                logger.info(f"DRY RUN for {match_id}")
                return {
                    "match": {
                        "match_id": match.match_id,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
                    },
                    "input_data": analysis_input.model_dump(),
                    "prompt_length": len(prompt),
                    "dry_run": True,
                }
            
            logger.info(f"Calling LLM for {match_id}...")
            runner = AnalysisRunner()
            response = await runner.run(prompt)
            
            if not response:
                logger.error(f"LLM call failed for {match_id}")
                return None
            
            parser = OutputParser()
            output = parser.parse(response)
            
            if not output:
                logger.warning(f"Failed to parse LLM response for {match_id}")
                return None
            
            return {
                "match": {
                    "match_id": match.match_id,
                    "home_team": match.home_team,
                    "away_team": match.away_team,
                    "kickoff_time": match.kickoff_time.isoformat() if match.kickoff_time else None,
                },
                "input_data": analysis_input.model_dump(),
                "output_data": output.model_dump(),
                "timestamp": datetime.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error analyzing match {match_id}: {e}")
            return None

    async def run_batch_analysis(
        self,
        hours: int = 72,
        dry_run: bool = False,
        max_matches: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        logger.info(f"Starting batch analysis (next {hours} hours)")
        
        matches = await self.get_upcoming_matches(hours)
        
        if not matches:
            logger.warning("No matches found")
            return []
        
        if max_matches:
            matches = matches[:max_matches]
            logger.info(f"Limited to {max_matches} matches")
        
        results = []
        total = len(matches)
        
        for idx, match in enumerate(matches, 1):
            logger.info(f"Processing {idx}/{total}: {match.home_team} vs {match.away_team}")
            
            result = await self.analyze_match(match, dry_run=dry_run)
            
            if result:
                results.append(result)
            
            if idx < total:
                await asyncio.sleep(2)
        
        logger.info(f"Batch analysis complete: {len(results)}/{total} successful")
        return results

    def format_results(
        self,
        results: List[Dict[str, Any]],
        output_format: str = "terminal"
    ) -> str:
        if output_format == "json":
            return json.dumps(results, indent=2, ensure_ascii=False, default=str)
        
        lines = []
        lines.append("\n" + "=" * 80)
        lines.append("📊 BATCH ANALYSIS RESULTS")
        lines.append("=" * 80)
        lines.append(f"\nTotal matches analyzed: {len(results)}")
        lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("\n")
        
        for idx, result in enumerate(results, 1):
            match = result.get("match", {})
            home = match.get("home_team", "?")
            away = match.get("away_team", "?")
            date = match.get("date", "?")
            hours_ahead = match.get("hours_ahead", 0)
            
            lines.append(f"\n[{idx}] {home} vs {away}")
            lines.append(f"    Date: {date} (+{hours_ahead}h)")
            lines.append(f"    Match ID: {match.get('match_id', 'N/A')}")
            
            if result.get("dry_run"):
                lines.append(f"    Status: DRY RUN (prompt length: {result.get('prompt_length', 0)})")
            else:
                output = result.get("output_data", {})
                decision = output.get("decision", {})
                lines.append(f"    Status: Analyzed")
                
                if decision:
                    best_bet = decision.get("best_bet", "")
                    confidence = decision.get("confidence", 0)
                    ev = decision.get("ev", 0)
                    lines.append(f"    Recommendation: {best_bet}")
                    lines.append(f"    Confidence: {confidence}/90")
                    lines.append(f"    EV: {ev:.3f}")
        
        lines.append("\n" + "=" * 80)
        return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Batch analyze upcoming football matches")
    parser.add_argument("--hours", type=int, default=72, help="Hours ahead to look for matches (default: 72)")
    parser.add_argument("--max-matches", type=int, help="Maximum number of matches to analyze")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no LLM call)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", type=str, help="Save results to file")
    return parser.parse_args()


async def main():
    args = parse_args()
    
    logger.info("=" * 60)
    logger.info("GOALCAST AI - BATCH ANALYSIS")
    logger.info("=" * 60)
    
    analyzer = BatchAnalyzer()
    
    results = await analyzer.run_batch_analysis(
        hours=args.hours,
        dry_run=args.dry_run,
        max_matches=args.max_matches,
    )
    
    output = analyzer.format_results(results, "json" if args.json else "terminal")
    print(output)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        logger.info(f"Results saved to: {output_path}")
    
    logger.info("Batch analysis complete")


if __name__ == "__main__":
    asyncio.run(main())
