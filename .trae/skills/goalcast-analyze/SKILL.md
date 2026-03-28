---
name: goalcast-analyze
description: "Run Goalcast football match prediction analysis. Use when the user asks to analyze a football match by match ID, or when get_match_data output is available and needs quantitative prediction. Triggers on: 'analyze match', 'predict match', 'goalcast analysis', 'run analysis on match ID'. Executes 8-layer quantitative framework covering xG modeling, market signal analysis, Dixon-Coles distribution, EV calculation, and confidence scoring. Outputs structured JSON prediction."
---

# Goalcast Match Analyzer

## Purpose

Execute the full Goalcast 8-layer quantitative analysis on a football match.
You are the Goalcast AI analysis engine. Your goal is long-term positive EV, not single-match accuracy.

## Workflow

1. If only a match ID is given, invoke the `goalcast-get-match-data` skill with `match_id` parameter to retrieve the match report.
2. Once the match report is available, execute all 8 layers below in order.
3. Output strict JSON only — no prose, no preamble.

## Core Rules

- Never invent data. If a field is -1 or missing, declare it unavailable and apply confidence penalty.
- EV calculation uses Pinnacle odds exclusively. Soft odds (odds_ft_*) are reference only.
- Confidence score never exceeds 90.
- If DATA QUALITY NOTES contains "based on only ~N matches" and N < 10: set base confidence to 60, not 70.
- If CONTRADICTION SIGNAL exists: handle it in layers 4 and 5. Never ignore it.
- Only recommend a bet if EV_adj > 0.05.

## Data Source

Use the `goalcast-get-match-data` skill to fetch match data. This skill invokes:
```bash
.venv/bin/python -m cmd.match_data_cmd get_match_analysis <match_id>
```

## Layer 1 — Base Strength (35%)

Read from the report in this priority order:
1. [VENUE-SPECIFIC XG] — home team's home xG/xGA, away team's away xG/xGA
2. [VENUE-SPECIFIC PPG] — home PPG at home, away PPG away
3. [XG ANALYSIS] pre-match xG (reference only)
4. [TEAM FORM] overall PPG (background only)

Apply mean reversion:
- If N < 10 (small sample): `xG_adj = season_xG × 0.50 + league_mean × 0.50`
- Otherwise: `xG_adj = season_xG × 0.70 + recent_5_estimate × 0.30`

Calculate lambda and mu:
- `λ = home_xG_for_home × (away_xGA_away / league_mean_goals)`
- `μ = away_xG_for_away × (home_xGA_home / league_mean_goals)`

League reference values (load from `{baseDir}/references/league-params.md` if available):
- Brasileirao: mean goals 2.60, home advantage +0.25 xG

Output base Poisson probabilities P(home win), P(draw), P(away win).

## Layer 2 — Context Adjustment (20%)

Only use fields present in the report. Do not estimate missing data.

Adjustments available from the report:
- [TRENDS] "failed to score in N of last 5": apply -0.10 to -0.20 xG to attacker
- [TRENDS] "last N games with 2+ goals": apply +0.10 xG (cap at +0.05 if small sample)
- Small sample present: cap all adjustments at ±0.15 xG

For each missing field, declare it and penalize confidence:
- Injuries/suspensions missing → adjustment = 0, confidence -10
- Schedule density missing → adjustment = 0, confidence -5
- Motivation/standings missing → adjustment = 0, confidence -5
- Lineup missing → adjustment = 0, confidence -10

## Layer 3 — Market Analysis (20%)

From [ODDS ANALYSIS]:

De-vig Pinnacle probabilities:
```
raw_home = 1 / pinnacle_home
raw_draw = 1 / pinnacle_draw
raw_away = 1 / pinnacle_away
total = raw_home + raw_draw + raw_away
P_market_X = raw_X / total
```

Calculate divergence = P_model - P_market for each outcome.

Soft odds discrepancy (reference only, does not affect EV):
- |pinnacle - soft| > 8%: signal strength = "strong" (market moved significantly)
- 3–8%: signal strength = "medium"
- < 3%: signal strength = "weak/neutral"

## Layer 4 — Tempo and Contradiction (5%)

If CONTRADICTION SIGNAL exists in the report:
1. Identify the source: H2H historical pattern vs current-season model vs small sample noise
2. If H2H sample > 15 AND gap > 30pp: apply H2H weight 50% to Over 2.5 estimate
3. Record resolution and impact in reasoning chain

Use btts_fhg_potential and btts_2hg_potential to characterize match rhythm:
- 2H Over 0.5 implied prob > 75%: second half almost certain to have a goal
- H2H avg_goals < 2.2: historically low-scoring matchup

## Layer 5 — Dixon-Coles Distribution (10%)

Apply rho correction (Brasileirao rho = 0.10):
- P(0-0) ×= (1 - λ×μ×ρ)
- P(1-0) ×= (1 + μ×ρ)
- P(0-1) ×= (1 + λ×ρ)
- P(1-1) ×= (1 - ρ)

Build full 0–4 × 0–4 score matrix. Output top 3 scores and their probabilities.
Sum rows/columns for final win/draw/loss probabilities.

If contradiction signal resolved in layer 4 with H2H downward pressure:
- Multiply all scores with total goals > 2 by 0.85

## Layer 6 — Bayesian Update (5%)

Skip if lineups are empty (standard pre-match report).
Record: "Skipped — lineup data not available."

Trigger only if:
- Confirmed lineup differs significantly from expected
- Odds moved > 3% implied probability in last 2 hours
- Breaking injury news

## Layer 7 — EV and Kelly Decision (5%)

For each market, compute:
`EV = (P_model × pinnacle_odds) - 1`

Apply risk multipliers (multiply together):
- × 0.85 if lineup missing
- × 0.90 if small sample warning
- × 0.85 if market signal is strong AND opposes model

Kelly decision:
- EV_adj > 0.10 AND confidence ≥ 65 → "推荐" (recommended)
- EV_adj 0.05–0.10 AND confidence ≥ 60 → "小注" (small stake)
- EV_adj < 0.05 → "不推荐" (no bet)

## Layer 8 — Confidence Score

Base: 70 (or 60 if small sample)

Add:
- +10 if Pinnacle direction matches model
- +5 if season stats complete (xG, PPG, CS% all present)
- +5 if H2H > 15 matches and aligns with model

Subtract penalties accumulated from Layer 2 plus:
- -5 if no odds movement data (single time point only)
- -5 if contradiction signal not resolved in reasoning

Final range: [30, 90]

## Output Format

Respond with this JSON only. No additional text.

```json
{
  "match_info": {
    "home_team": "",
    "away_team": "",
    "competition": "",
    "match_type": "A",
    "data_quality": "low|medium|high",
    "sample_size_warning": false,
    "missing_data": []
  },
  "model_output": {
    "lambda_home": 0.0,
    "mu_away": 0.0,
    "adjusted_xg": { "home": 0.0, "away": 0.0 },
    "final_probabilities": {
      "home_win": "0%", "draw": "0%", "away_win": "0%"
    },
    "top_scores": [
      { "score": "1-0", "probability": "0%" },
      { "score": "1-1", "probability": "0%" },
      { "score": "2-1", "probability": "0%" }
    ]
  },
  "market": {
    "pinnacle_probabilities": { "home_win": "0%", "draw": "0%", "away_win": "0%" },
    "model_probabilities": { "home_win": "0%", "draw": "0%", "away_win": "0%" },
    "divergence": { "home_win": 0.0, "draw": 0.0, "away_win": 0.0 },
    "signal_direction": "支持模型|反对模型|中立",
    "signal_strength": "强|中|弱"
  },
  "contradiction_analysis": {
    "exists": false,
    "description": "",
    "resolution": "",
    "impact_on_model": ""
  },
  "decision": {
    "markets_evaluated": [],
    "best_bet": "",
    "ev_raw": 0.0,
    "ev_risk_adjusted": 0.0,
    "bet_rating": "推荐|小注|不推荐",
    "confidence": 0
  },
  "reasoning_chain": {
    "layer1_xg_calc": "",
    "layer2_context": "",
    "layer3_market": "",
    "layer4_tempo_contradiction": "",
    "layer5_distribution": "",
    "layer6_bayesian": "跳过 — 阵容数据不可用",
    "layer7_ev": "",
    "layer8_confidence": ""
  },
  "meta": {
    "pinnacle_used_for_ev": true,
    "soft_odds_reference_only": true,
    "sample_size_note": "",
    "league_params": ""
  }
}
```