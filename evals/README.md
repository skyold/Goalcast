# Evals

Regression fixtures for math/algorithm correctness that survives across
implementation changes. These are **not** unit tests — they are input → expected
output specifications that any runner (pytest, custom script, CI job) can
consume.

Why a separate folder from `backend/tests/`:

- Tests pin internal behavior. Evals pin **observable contracts**.
- Tests are written alongside code. Evals are written alongside the **product
  promise** (e.g. "the edge our UI shows is mathematically what the formula
  computes — and small rounding does not silently move a bet from +EV to −EV").
- Evals are language-agnostic. The same JSONL fixture runs from a Python
  backend runner today and a TypeScript frontend runner tomorrow.

## Files

| File                       | Subject under eval                         | Source                                  |
|----------------------------|--------------------------------------------|-----------------------------------------|
| `value_bet_edge.jsonl`     | `compute_edge(prob, odds)` percentage edge | `backend/services/value_bets.py:1`      |

## Fixture format

One JSON object per line. Required keys:

- `id` — stable, descriptive identifier
- `inputs` — kwargs to the function under eval
- `expected` — the exact return value
- `note` — one-line description of *why* this case matters

## Running

There is no runner checked in yet (intentional — evals are specs first). The
simplest way to consume:

```python
import json
from services.value_bets import compute_edge

with open("evals/value_bet_edge.jsonl") as f:
    for line in f:
        case = json.loads(line)
        got = compute_edge(**case["inputs"])
        assert got == case["expected"], f"{case['id']}: got {got}, want {case['expected']}"
```

Add new fixtures whenever a bug, edge case, or domain-rule clarification
reveals a behavior that should never silently regress.
