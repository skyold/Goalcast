import asyncio
import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Any, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.provider.footystats.client import FootyStatsProvider
from src.datasource.footystats.match_datasource import MatchDataDataSource


class MatchDataCMD:
    def __init__(self, debug: bool = False):
        self.provider = FootyStatsProvider(debug=debug)
        self.datasource = MatchDataDataSource(self.provider, debug=debug)
        self.debug = debug
        self._raw_data: Dict[str, Any] = {}

    async def get_schedule(self, days: int = 7):
        matches = await self.datasource.get_recent_matches(days)
        self._print_matches(matches)

    async def get_match_basic(self, match_id: int):
        data = await self.datasource.get_match_basic(match_id)
        if data:
            if self.debug:
                raw = self.datasource.get_raw_data('basic')
                if raw:
                    self._print_raw_data('basic', raw)
            self._print_basic(data)

    async def get_match_stats(self, match_id: int):
        data = await self.datasource.get_match_stats(match_id)
        if data:
            if self.debug:
                raw = self.datasource.get_raw_data('stats')
                if raw:
                    self._print_raw_data('stats', raw)
            self._print_stats(data)

    async def get_match_advanced(self, match_id: int):
        data = await self.datasource.get_match_advanced(match_id)
        if data:
            if self.debug:
                raw = self.datasource.get_raw_data('advanced')
                if raw:
                    self._print_raw_data('advanced', raw)
            self._print_advanced(data)

    async def get_match_odds(self, match_id: int):
        data = await self.datasource.get_match_odds(match_id)
        if data:
            if self.debug:
                raw = self.datasource.get_raw_data('odds')
                if raw:
                    self._print_raw_data('odds', raw)
            self._print_odds(data)

    async def get_match_teams(self, match_id: int):
        data = await self.datasource.get_match_teams(match_id)
        if data:
            self._print_teams(data)

    async def get_match_analysis(self, match_id: int):
        data = await self.datasource.get_full_match_data(match_id)
        if data:
            if self.debug:
                for category in ['basic', 'stats', 'advanced', 'odds']:
                    raw = self.datasource.get_raw_data(category)
                    if raw:
                        self._print_raw_data(category, raw)
            self._print_analysis(data)

    async def get_match_others(self, match_id: int):
        data = await self.datasource.get_match_others(match_id)
        if data:
            self._print_others(data)

    async def get_full_match(self, match_id: int):
        data = await self.datasource.get_full_match_data(match_id)
        if data:
            if self.debug:
                for category in ['basic', 'stats', 'advanced', 'odds']:
                    raw = self.datasource.get_raw_data(category)
                    if raw:
                        self._print_raw_data(category, raw)
            self._print_full(data)

    def _print_raw_data(self, category: str, raw_data: Any):
        """打印原始 API 数据"""
        print(f"\n{'='*60}")
        print(f"=== RAW DATA: {category} ===")
        print(f"{'='*60}")
        print(json.dumps(raw_data, indent=2, default=str, ensure_ascii=False))

    def _print_matches(self, matches):
        print("\n=== 比赛列表 ===")
        for match in matches:
            print(f"[{match.match_id}] {match.home_team_name} vs {match.away_team_name}")
            print(f"  时间：{match.match_time}")
            print(f"  比分：{match.home_score} - {match.away_score}")
            print()

    def _print_basic(self, data):
        print(f"\n=== 比赛信息 ===")
        print(f"比赛：{data.home_team_name} vs {data.away_team_name}")
        print(f"时间：{data.match_time}")
        print(f"比分：{data.home_score} - {data.away_score}")
        print(f"状态：{data.status}")
        print(f"球场：{data.venue or 'N/A'}")

    def _print_stats(self, data):
        print(f"\n=== 统计数据 ===")
        if data.has_valid_stats:
            print(f"控球率：{data.home_possession}% - {data.away_possession}%")
            print(f"射门：{data.home_total_shots} - {data.away_total_shots}")
            print(f"射正：{data.home_shots_on_target} - {data.away_shots_on_target}")
            print(f"角球：{data.home_corners} - {data.away_corners}")
            print(f"黄牌：{data.home_yellow_cards} - {data.away_yellow_cards}")
            print(f"BTTS: {'是' if data.btts else '否'}")
            print(f"Over 2.5: {'是' if data.over_25 else '否'}")
        else:
            print("比赛尚未进行或无统计数据")

    def _print_advanced(self, data):
        print(f"\n=== 高级数据 ===")
        if data.has_xg_prematch:
            print(f"赛前预期进球 xG: {data.home_xg_prematch:.2f} - {data.away_xg_prematch:.2f} (总和: {data.total_xg_prematch:.2f})")
        if data.has_xg:
            print(f"实际进球期望 xG: {data.home_xg:.2f} - {data.away_xg:.2f} (总和: {data.total_xg:.2f})")
        if data.home_attacks is not None and data.home_attacks > 0:
            print(f"进攻：{data.home_attacks} - {data.away_attacks}")
        else:
            print(f"进攻：{data.home_attacks or 0} - {data.away_attacks or 0}")
        if data.home_dangerous_attacks is not None and data.home_dangerous_attacks > 0:
            print(f"危险进攻：{data.home_dangerous_attacks} - {data.away_dangerous_attacks}")
        else:
            print(f"危险进攻：{data.home_dangerous_attacks or 0} - {data.away_dangerous_attacks or 0}")
        if data.has_lineups:
            print(f"主队首发：{len(data.home_lineup)} 人")
            print(f"客队首发：{len(data.away_lineup)} 人")
        if data.home_trends or data.away_trends:
            print(f"\n--- 球队趋势分析 ---")
            if data.home_trends:
                print(f"主队 (home) 趋势：")
                for trend in data.home_trends[:3]:
                    print(f"  • {trend}")
            if data.away_trends:
                print(f"客队 (away) 趋势：")
                for trend in data.away_trends[:3]:
                    print(f"  • {trend}")

    def _print_odds(self, data):
        print(f"\n=== 赔率数据 ===")
        if data.odds_home:
            print(f"主胜：{data.odds_home:.2f} (隐含概率 {data.implied_prob_home:.1%})")
            print(f"平局：{data.odds_draw:.2f} (隐含概率 {data.implied_prob_draw:.1%})")
            print(f"客胜：{data.odds_away:.2f} (隐含概率 {data.implied_prob_away:.1%})")
        if data.over_25_odds:
            print(f"大球 2.5: {data.over_25_odds:.2f}")
            print(f"小球 2.5: {data.under_25_odds:.2f}")

    def _print_teams(self, data):
        print(f"\n=== 球队数据 ===")
        if data.home_form:
            print(f"主队近 5 场：{data.home_form.last_5_wins}胜{data.home_form.last_5_draws}平{data.home_form.last_5_losses}负")
            print(f"主队场均积分：{data.home_form.last_5_ppg:.2f}")
        if data.away_form:
            print(f"客队近 5 场：{data.away_form.last_5_wins}胜{data.away_form.last_5_draws}平{data.away_form.last_5_losses}负")
            print(f"客队场均积分：{data.away_form.last_5_ppg:.2f}")
        print(f"交锋记录：{data.h2h_total} 场")
        print(f"主队胜：{data.h2h_home_wins} | 客队胜：{data.h2h_away_wins} | 平局：{data.h2h_draws}")

        if data.home_season_stats:
            home_stats = data.home_season_stats
            print(f"\n主队赛季统计：")
            print(f"  排名：{home_stats.position} | 积分：{home_stats.points} | 场均得分：{home_stats.ppg:.2f}")
            print(f"  战绩：{home_stats.wins}胜 {home_stats.draws}平 {home_stats.losses}负")
            print(f"  进球：{home_stats.goals_scored} | 失球：{home_stats.goals_conceded} | 场均进球：{home_stats.avg_goals_scored:.2f}")
            print(f"  xG：主场 {home_stats.xg_for_avg_home:.2f} / 客场 {home_stats.xg_for_avg_away:.2f} / 平均 {home_stats.xg_for_avg_overall:.2f}")
            print(f"  xGA：主场 {home_stats.xg_against_avg_home:.2f} / 客场 {home_stats.xg_against_avg_away:.2f} / 平均 {home_stats.xg_against_avg_overall:.2f}")

        if data.away_season_stats:
            away_stats = data.away_season_stats
            print(f"\n客队赛季统计：")
            print(f"  排名：{away_stats.position} | 积分：{away_stats.points} | 场均得分：{away_stats.ppg:.2f}")
            print(f"  战绩：{away_stats.wins}胜 {away_stats.draws}平 {away_stats.losses}负")
            print(f"  进球：{away_stats.goals_scored} | 失球：{away_stats.goals_conceded} | 场均进球：{away_stats.avg_goals_scored:.2f}")
            print(f"  xG：主场 {away_stats.xg_for_avg_home:.2f} / 客场 {away_stats.xg_for_avg_away:.2f} / 平均 {away_stats.xg_for_avg_overall:.2f}")
            print(f"  xGA：主场 {away_stats.xg_against_avg_home:.2f} / 客场 {away_stats.xg_against_avg_away:.2f} / 平均 {away_stats.xg_against_avg_overall:.2f}")

    def _print_others(self, data):
        print(f"\n=== 其他数据 ===")

    def _print_full(self, data):
        if data.basic:
            self._print_basic(data.basic)
        if data.stats:
            self._print_stats(data.stats)
        if data.advanced:
            self._print_advanced(data.advanced)
        if data.odds:
            self._print_odds(data.odds)
        if data.teams:
            self._print_teams(data.teams)
        if data.others:
            self._print_others(data.others)

    def _print_analysis(self, data):
        print(f"\n{'='*60}")
        print(f"=== MATCH ANALYSIS: {data.basic.match_id} ===")
        print(f"{'='*60}")

        if data.basic:
            print(f"\n[BASIC INFO]")
            print(f"  {data.basic.home_team_name} vs {data.basic.away_team_name}")
            print(f"  Time: {data.basic.match_time}")
            print(f"  Status: {data.basic.status}")
            if data.basic.home_score and data.basic.away_score is not None:
                print(f"  Score: {data.basic.home_score} - {data.basic.away_score}")

        if data.advanced and data.advanced.has_xg_prematch:
            print(f"\n[XG ANALYSIS]")
            print(f"  Pre-match xG (system estimate): Home {data.advanced.home_xg_prematch:.2f} / Away {data.advanced.away_xg_prematch:.2f}")
            print(f"  Total xG: {data.advanced.total_xg_prematch:.2f}")
            print(f"  xG Difference: {data.advanced.xg_difference:+.2f} (positive=home advantage)")

        if data.teams:
            print(f"\n[TEAM FORM]")
            if data.teams.home_season_stats and data.teams.away_season_stats:
                home_stats = data.teams.home_season_stats
                away_stats = data.teams.away_season_stats
                print(f"  Home Team (Position: {home_stats.position})")
                print(f"    PPG: {home_stats.ppg:.2f} | Win%: {home_stats.win_percentage_overall:.1f}%")
                print(f"    Goals: {home_stats.goals_scored} | Conceded: {home_stats.goals_conceded}")
                print(f"    Avg Goals: {home_stats.avg_goals_scored:.2f} | Avg Conceded: {home_stats.avg_goals_conceded:.2f}")
                print(f"  Away Team (Position: {away_stats.position})")
                print(f"    PPG: {away_stats.ppg:.2f} | Win%: {away_stats.win_percentage_overall:.1f}%")
                print(f"    Goals: {away_stats.goals_scored} | Conceded: {away_stats.goals_conceded}")
                print(f"    Avg Goals: {away_stats.avg_goals_scored:.2f} | Avg Conceded: {away_stats.avg_goals_conceded:.2f}")
                print(f"  PPG Difference (overall): {data.teams.strength_difference:+.2f}")

            if data.advanced:
                print(f"\n[VENUE-SPECIFIC PPG] (Home team at home / Away team away)")
                if data.advanced.home_ppg is not None:
                    print(f"  Home team HOME PPG: {data.advanced.home_ppg:.2f}")
                if data.advanced.away_ppg is not None:
                    print(f"  Away team AWAY PPG: {data.advanced.away_ppg:.2f}")
                if data.advanced.home_ppg is not None and data.advanced.away_ppg is not None:
                    venue_ppg_diff = data.advanced.home_ppg - data.advanced.away_ppg
                    print(f"  Venue PPG Difference: {venue_ppg_diff:+.2f} (big difference = strong home advantage signal)")

            if data.teams.home_season_stats and data.teams.home_season_stats.home_attack_advantage:
                adv = data.teams.home_season_stats
                print(f"\n[HOME ADVANTAGE]")
                print(f"  Attack Advantage: {adv.home_attack_advantage:+d}")
                print(f"  Defence Advantage: {adv.home_defence_advantage:+d}")
                print(f"  Overall Advantage: {adv.home_overall_advantage:+d}")

            print(f"\n[H2H RECORD]")
            print(f"  Total Matches: {data.teams.h2h_total}")
            print(f"  Home Wins: {data.teams.h2h_home_wins} ({data.teams.h2h_home_win_percentage:.1f}%)")
            print(f"  Away Wins: {data.teams.h2h_away_wins} ({data.teams.h2h_away_win_percentage:.1f}%)")
            print(f"  Draws: {data.teams.h2h_draws} ({data.teams.h2h_draw_percentage:.1f}%)")
            print(f"  Avg Goals: {data.teams.h2h_avg_goals:.2f}")
            print(f"  H2H BTTS %: {data.teams.h2h_btts_percentage:.1f}%")
            print(f"  H2H Over 2.5 %: {data.teams.h2h_over_25_percentage:.1f}%")

        if data.advanced:
            print(f"\n[POTENTIALS & CONTRADICTIONS]")
            if data.advanced.btts_potential is not None:
                print(f"  BTTS Potential (full match): {data.advanced.btts_potential}%")
            if data.advanced.btts_fhg_potential is not None:
                print(f"  BTTS Potential (1st half): {data.advanced.btts_fhg_potential}%")
            if data.advanced.btts_2hg_potential is not None:
                print(f"  BTTS Potential (2nd half): {data.advanced.btts_2hg_potential}%")
            if data.advanced.o25_potential is not None:
                print(f"  Over 2.5 Potential: {data.advanced.o25_potential}%")
            if data.advanced.o35_potential is not None:
                print(f"  Over 3.5 Potential: {data.advanced.o35_potential}%")
            if data.advanced.u25_potential is not None:
                print(f"  Under 2.5 Potential: {data.advanced.u25_potential}%")
            if data.advanced.corners_potential is not None:
                print(f"  Corners Potential: {data.advanced.corners_potential:.1f}")
            if data.advanced.avg_potential is not None:
                print(f"  Avg Goals Potential: {data.advanced.avg_potential:.1f}")

            if data.teams and data.teams.h2h_over_25_percentage > 0 and data.advanced.o25_potential:
                diff = data.advanced.o25_potential - data.teams.h2h_over_25_percentage
                print(f"\n  *** CONTRADICTION SIGNAL ***")
                print(f"  H2H Over 2.5: {data.teams.h2h_over_25_percentage:.0f}% vs Potential: {data.advanced.o25_potential}%")
                print(f"  Difference: {diff:+.0f}pp - H2H suggests LOW scoring, but model predicts HIGHER")

        if data.teams and data.teams.home_season_stats:
            stats = data.teams.home_season_stats
            print(f"\n[HOME TEAM DETAILED STATS]")
            print(f"  Clean Sheet %: {stats.clean_sheet_percentage_overall:.1f}% (H: {stats.clean_sheet_percentage_home:.1f}% | A: {stats.clean_sheet_percentage_away:.1f}%)")
            print(f"  BTTS %: {stats.btts_percentage_overall:.1f}% (H: {stats.btts_percentage_home:.1f}% | A: {stats.btts_percentage_away:.1f}%)")
            print(f"  Over 2.5 %: {stats.over_25_percentage_overall:.1f}% (H: {stats.over_25_percentage_home:.1f}% | A: {stats.over_25_percentage_away:.1f}%)")
            print(f"  Season BTTS: {stats.btts_percentage_overall:.0f}% (season data, more recent than H2H)")
            print(f"  HT Leading %: {stats.leading_at_ht_percentage_overall:.1f}%")
            print(f"  Win% (H/A): {stats.win_percentage_home:.1f}% / {stats.win_percentage_away:.1f}%")

        if data.teams and data.teams.away_season_stats:
            stats = data.teams.away_season_stats
            print(f"\n[AWAY TEAM DETAILED STATS]")
            print(f"  Clean Sheet %: {stats.clean_sheet_percentage_overall:.1f}% (H: {stats.clean_sheet_percentage_home:.1f}% | A: {stats.clean_sheet_percentage_away:.1f}%)")
            print(f"  BTTS %: {stats.btts_percentage_overall:.1f}% (H: {stats.btts_percentage_home:.1f}% | A: {stats.btts_percentage_away:.1f}%)")
            print(f"  Over 2.5 %: {stats.over_25_percentage_overall:.1f}% (H: {stats.over_25_percentage_home:.1f}% | A: {stats.over_25_percentage_away:.1f}%)")
            print(f"  Season BTTS: {stats.btts_percentage_overall:.0f}% (season data, more recent than H2H)")
            print(f"  HT Leading %: {stats.leading_at_ht_percentage_overall:.1f}%")
            print(f"  Win% (H/A): {stats.win_percentage_home:.1f}% / {stats.win_percentage_away:.1f}%")

        if data.teams and data.teams.home_season_stats and data.teams.away_season_stats:
            home_stats = data.teams.home_season_stats
            away_stats = data.teams.away_season_stats
            print(f"\n[VENUE-SPECIFIC XG]")
            print(f"  Home team xG FOR (home): {home_stats.xg_for_avg_home:.2f}")
            print(f"  Home team xG AGAINST (home): {home_stats.xg_against_avg_home:.2f}")
            print(f"  Away team xG FOR (away): {away_stats.xg_for_avg_away:.2f}")
            print(f"  Away team xG AGAINST (away): {away_stats.xg_against_avg_away:.2f}")
            if data.advanced and data.advanced.home_xg_prematch:
                print(f"  Note: Pre-match xG {data.advanced.home_xg_prematch:.2f} may differ from venue-specific xG")

        if data.odds:
            print(f"\n[ODDS ANALYSIS]")

            if data.odds.has_pinnacle_odds:
                p = data.odds.pinnacle_odds
                print(f"  *** PINNACLE ODDS (Smart Money Benchmark) ***")
                print(f"  Pinnacle: Home {p.home:.2f} | Draw {p.draw:.2f} | Away {p.away:.2f}")
                print(f"  Pinnacle Implied Prob: Home {p.implied_prob_home:.1%} | Draw {p.implied_prob_draw:.1%} | Away {p.implied_prob_away:.1%}")
            else:
                print(f"  WARNING: Pinnacle odds not available")

            if data.odds.has_full_1x2_odds:
                odds = data.odds
                odds.calculate_implied_probabilities()
                print(f"\n  [SOFT BOOK ODDS (odds_ft_*)]")
                print(f"  Soft Odds: Home {odds.odds_home:.2f} | Draw {odds.odds_draw:.2f} | Away {odds.odds_away:.2f}")
                print(f"  Soft Implied Prob: {odds.implied_prob_home:.1%} | {odds.implied_prob_draw:.1%} | {odds.implied_prob_away:.1%}")
                if data.odds.has_pinnacle_odds:
                    p = data.odds.pinnacle_odds
                    diff_home = p.implied_prob_home - odds.implied_prob_home
                    diff_away = p.implied_prob_away - odds.implied_prob_away
                    print(f"  *** DISCREPANCY ***")
                    print(f"  Pinnacle vs Soft Home: {diff_home:+.1%}")
                    print(f"  Pinnacle vs Soft Away: {diff_away:+.1%}")
                    if abs(diff_home) > 0.05:
                        print(f"  NOTE: Large discrepancy - soft odds may be outdated or wrong")

            if odds.has_btts_odds:
                print(f"  BTTS: Yes {odds.btts_yes_odds:.2f} | No {odds.btts_no_odds:.2f}")
            if odds.has_over_25_odds:
                print(f"  Over 2.5: {odds.over_25_odds:.2f} | Under 2.5: {odds.under_25_odds:.2f}")
            if odds.has_ht_odds:
                print(f"  HT 1X2: {odds.odds_1st_half_result_1:.2f} | {odds.odds_1st_half_result_x:.2f} | {odds.odds_1st_half_result_2:.2f}")
            if odds.has_corners_odds:
                print(f"  Corners O95: {odds.odds_corners_over_95:.2f} | O105: {odds.odds_corners_over_105:.2f} | O115: {odds.odds_corners_over_115:.2f}")
            if odds.odds_doublechance_1x:
                print(f"  DC 1X: {odds.odds_doublechance_1x:.2f} | X2: {odds.odds_doublechance_x2:.2f}")
            if odds.odds_win_to_nil_1:
                print(f"  Win to Nil: Home {odds.odds_win_to_nil_1:.2f} | Away {odds.odds_win_to_nil_2:.2f}")
            if odds.odds_corners_1:
                print(f"  Corners 1X2: Home {odds.odds_corners_1:.2f} | Draw {odds.odds_corners_x:.2f} | Away {odds.odds_corners_2:.2f}")

        if data.advanced:
            if data.advanced.home_trends or data.advanced.away_trends:
                print(f"\n[TRENDS]")
                if data.advanced.home_trends:
                    print(f"  Home Team Trends:")
                    for trend in data.advanced.home_trends[:3]:
                        print(f"    - {trend}")
                if data.advanced.away_trends:
                    print(f"  Away Team Trends:")
                    for trend in data.advanced.away_trends[:3]:
                        print(f"    - {trend}")

        print(f"\n{'='*60}")
        print(f"[SUMMARY - KEY SIGNALS]")
        print(f"{'='*60}")
        if data.odds and data.odds.has_pinnacle_odds:
            p = data.odds.pinnacle_odds
            print(f"  Pinnacle odds show Home {p.home:.2f} / Away {p.away:.2f}")
            if p.home < 2.0:
                print(f"  -> Market favors HOME strongly")
            if p.away > 3.5:
                print(f"  -> Market disfavors AWAY significantly")
        if data.teams and data.teams.h2h_over_25_percentage > 0 and data.advanced and data.advanced.o25_potential:
            diff = data.advanced.o25_potential - data.teams.h2h_over_25_percentage
            if abs(diff) > 20:
                print(f"  -> Over 2.5 CONTRADICTION: H2H {data.teams.h2h_over_25_percentage:.0f}% vs Potential {data.advanced.o25_potential}%")
        if data.advanced and data.advanced.home_ppg and data.advanced.away_ppg:
            ppg_diff = data.advanced.home_ppg - data.advanced.away_ppg
            if abs(ppg_diff) > 1.0:
                print(f"  -> LARGE PPG difference: {ppg_diff:+.2f}")

        if data.odds:
            odds = data.odds
            print(f"\n[2ND HALF ODDS]")
            if odds.odds_2nd_half_result_1:
                print(f"  2H Result: {odds.odds_2nd_half_result_1:.2f} | {odds.odds_2nd_half_result_x:.2f} | {odds.odds_2nd_half_result_2:.2f}")
            if odds.odds_2nd_half_over05:
                print(f"  2H Over 0.5: {odds.odds_2nd_half_over05:.2f} (implied prob: {(1/odds.odds_2nd_half_over05)*100:.0f}%)")
            if odds.odds_2nd_half_over15:
                print(f"  2H Over 1.5: {odds.odds_2nd_half_over15:.2f}")

        print(f"\n{'='*60}")
        print(f"[DATA QUALITY NOTES]")
        print(f"{'='*60}")

        if data.advanced and data.advanced.matches_completed_minimum:
            sample_size = data.advanced.matches_completed_minimum
            print(f"  WARNING: Season stats based on only ~{sample_size} matches")
            print(f"  High variance - weight H2H history more heavily")
            print(f"  Small sample sizes reduce confidence in xG, PPG, CS% stats")

        if data.odds:
            odds = data.odds
            if odds.has_pinnacle_odds:
                print(f"\n  ODDS USAGE NOTE:")
                print(f"  - Pinnacle: Use for EV calculation (smart money benchmark)")
                print(f"  - Soft odds (odds_ft_*): Reference only, may be outdated")
                if odds.odds_home and odds.odds_draw and odds.odds_away:
                    print(f"  - Soft odds: Home {odds.odds_home:.2f} / Draw {odds.odds_draw:.2f} / Away {odds.odds_away:.2f}")

        print(f"{'='*60}")


def add_debug_arg(subparser):
    """为子命令添加 debug 参数"""
    subparser.add_argument('--debug', action='store_true', help='显示原始 API 数据')


async def main():
    parser = argparse.ArgumentParser(
        description="Match Data 命令行工具 - 按类别获取比赛数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python3 -m cmd.match_data_cmd get_schedule --days 3
  python3 -m cmd.match_data_cmd get_match_basic 8409849
  python3 -m cmd.match_data_cmd get_match_advanced 8409849 --debug
  python3 -m cmd.match_data_cmd get_full_match 8409849 --debug
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    p_schedule = subparsers.add_parser('get_schedule', help='获取最近N天比赛列表')
    p_schedule.add_argument('--days', type=int, default=7, help='天数 (默认: 7)')
    add_debug_arg(p_schedule)

    p_basic = subparsers.add_parser('get_match_basic', help='获取比赛基础信息')
    p_basic.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_basic)

    p_stats = subparsers.add_parser('get_match_stats', help='获取比赛统计数据')
    p_stats.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_stats)

    p_advanced = subparsers.add_parser('get_match_advanced', help='获取高级数据')
    p_advanced.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_advanced)

    p_odds = subparsers.add_parser('get_match_odds', help='获取赔率数据')
    p_odds.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_odds)

    p_teams = subparsers.add_parser('get_match_teams', help='获取球队数据')
    p_teams.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_teams)

    p_others = subparsers.add_parser('get_match_others', help='获取其他数据')
    p_others.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_others)

    p_full = subparsers.add_parser('get_full_match', help='获取完整数据')
    p_full.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_full)

    p_analysis = subparsers.add_parser('get_match_analysis', help='获取完整分析数据（适合 Agent 分析）')
    p_analysis.add_argument('match_id', type=int, help='比赛 ID')
    add_debug_arg(p_analysis)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    debug = getattr(args, 'debug', False)
    cmd = MatchDataCMD(debug=debug)

    if args.command == 'get_schedule':
        await cmd.get_schedule(args.days)
    elif args.command == 'get_match_basic':
        await cmd.get_match_basic(args.match_id)
    elif args.command == 'get_match_stats':
        await cmd.get_match_stats(args.match_id)
    elif args.command == 'get_match_advanced':
        await cmd.get_match_advanced(args.match_id)
    elif args.command == 'get_match_odds':
        await cmd.get_match_odds(args.match_id)
    elif args.command == 'get_match_teams':
        await cmd.get_match_teams(args.match_id)
    elif args.command == 'get_match_others':
        await cmd.get_match_others(args.match_id)
    elif args.command == 'get_full_match':
        await cmd.get_full_match(args.match_id)
    elif args.command == 'get_match_analysis':
        await cmd.get_match_analysis(args.match_id)


if __name__ == '__main__':
    asyncio.run(main())
