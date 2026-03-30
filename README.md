# Goalcast

Football match analysis and prediction engine — 8-layer quantitative analysis system powered by multi-provider data and LLM.

## Installation

```bash
pip install goalcast[ai]
```

## Usage

```bash
# Query upcoming matches
goalcast-get-matches --next-days 7

# Analyze a specific match
goalcast-match --date 2026-03-30
```

## Features

- Multi-provider data aggregation (FootyStats, ESPN, Understat, Transfermarkt, ClubElo, and more)
- Layered datasource architecture with registry and caching
- Async-first design
- CLI entry points for quick access
