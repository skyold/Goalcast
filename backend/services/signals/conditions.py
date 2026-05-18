"""Conditions evaluator shared between forward (snapshot worker, Phase 4) and
backtest (Phase 3) paths. The fact that **the same function** decides "does
this signal_result pass the book/backtest conditions?" in both paths is the
load-bearing guarantee behind the PRD's "回测 ↔ forward 一致性 < 1pp" success
metric.

`conditions_json` v1 schema (see docs/PRD/signal-catalog-and-subscriptions
Solution Detail § conditions_json):

    {
      "strength_min": 0.5,
      "filters": [
        {"path": "value.delta_pct", "op": ">",  "value": 5},
        {"path": "value.selection", "op": "==", "value": "home"}
      ]
    }

Path whitelist:
  - "strength"      → signal_result["strength"]
  - "value.<key>"   → signal_result["value"][key]
                      (or json.loads(signal_result["value_json"])[key])

Op whitelist (Q2 — single layer AND, no DSL):
  ==  !=  >  >=  <  <=  in

Fail-closed semantics:
  - unknown path        → False
  - unknown op          → False
  - type mismatch       → False (e.g. comparing None with > / <)
  - missing strength    → False when strength_min specified
  - JSON parse failure  → value treated as {} (filters consulting it will
                          mostly return False, which is the safe outcome)
"""
from __future__ import annotations

import json
from typing import Any


def _numeric_cmp(a, b, op) -> bool:
    if a is None or b is None:
        return False
    try:
        return bool(op(a, b))
    except TypeError:
        return False


def _membership(a, b) -> bool:
    if a is None:
        return False
    try:
        return a in b
    except TypeError:
        return False


_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">":  lambda a, b: _numeric_cmp(a, b, lambda x, y: x >  y),
    ">=": lambda a, b: _numeric_cmp(a, b, lambda x, y: x >= y),
    "<":  lambda a, b: _numeric_cmp(a, b, lambda x, y: x <  y),
    "<=": lambda a, b: _numeric_cmp(a, b, lambda x, y: x <= y),
    "in": lambda a, b: _membership(a, b),
}


def _resolve_value(signal_result: dict) -> dict:
    """signal_result may carry either {"value": dict} (in-memory) or
    {"value_json": str} (DB-decoded row). Tolerate both."""
    if isinstance(signal_result.get("value"), dict):
        return signal_result["value"]
    raw = signal_result.get("value_json")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except (TypeError, ValueError):
        return {}


def _resolve_path(path: str, signal_result: dict, value: dict) -> Any:
    """Return the field at `path`, or None if path is malformed / missing."""
    if path == "strength":
        return signal_result.get("strength")
    if path.startswith("value."):
        key = path[len("value."):]
        if not key or "." in key:
            # No nested paths in v1 — keep evaluator boring & predictable.
            return None
        return value.get(key)
    return None  # unknown path prefix → caller treats as fail


def eval_conditions(conditions: dict, signal_result: dict) -> bool:
    """Return True iff the signal result satisfies all conditions.

    Empty conditions ({}) → True (every signal passes), which is the
    intended default for "House Book auto-follows the signal without
    further filtering".
    """
    if not isinstance(conditions, dict):
        return False

    if "strength_min" in conditions:
        s = signal_result.get("strength")
        try:
            if s is None or float(s) < float(conditions["strength_min"]):
                return False
        except (TypeError, ValueError):
            return False

    filters = conditions.get("filters") or []
    if filters:
        value = _resolve_value(signal_result)
        for f in filters:
            if not isinstance(f, dict):
                return False
            path = f.get("path")
            op   = f.get("op")
            val  = f.get("value")
            if not isinstance(path, str) or op not in _OPS:
                return False
            if path != "strength" and not path.startswith("value."):
                return False  # unknown prefix → fail closed
            actual = _resolve_path(path, signal_result, value)
            if not _OPS[op](actual, val):
                return False

    return True
