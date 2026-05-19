"""Unit tests for services/signals/conditions.eval_conditions.

These tests pin the contract that forward (snapshot worker) and backtest
(historical replay) share. Behaviour drift here = forward/backtest drift in
production, which would break PRD success metric "回测 ↔ forward 一致性 < 1pp".
"""
from __future__ import annotations

import json
import pytest

from services.signals.conditions import eval_conditions


# Synthetic signal_result fixtures — both representations of "value".
RESULT_INLINE = {"strength": 0.8, "value": {"delta_pct": 9.2, "selection": "home"}}
RESULT_JSON   = {"strength": 0.8,
                 "value_json": json.dumps({"delta_pct": 9.2, "selection": "home"})}


def test_empty_conditions_pass_everything():
    assert eval_conditions({}, RESULT_INLINE) is True


def test_strength_min_pass():
    assert eval_conditions({"strength_min": 0.5}, RESULT_INLINE) is True


def test_strength_min_fail():
    assert eval_conditions({"strength_min": 0.9}, RESULT_INLINE) is False


def test_strength_min_with_none_strength_fails():
    assert eval_conditions({"strength_min": 0.1}, {"strength": None, "value": {}}) is False


@pytest.mark.parametrize("rep", [RESULT_INLINE, RESULT_JSON])
def test_filter_gt_passes(rep):
    """Both 'value' dict and 'value_json' string representations work."""
    cond = {"filters": [{"path": "value.delta_pct", "op": ">", "value": 5}]}
    assert eval_conditions(cond, rep) is True


@pytest.mark.parametrize("rep", [RESULT_INLINE, RESULT_JSON])
def test_filter_gt_fails(rep):
    cond = {"filters": [{"path": "value.delta_pct", "op": ">", "value": 15}]}
    assert eval_conditions(cond, rep) is False


def test_filter_eq_string():
    cond = {"filters": [{"path": "value.selection", "op": "==", "value": "home"}]}
    assert eval_conditions(cond, RESULT_INLINE) is True
    cond_neq = {"filters": [{"path": "value.selection", "op": "==", "value": "away"}]}
    assert eval_conditions(cond_neq, RESULT_INLINE) is False


def test_filter_in_membership():
    cond = {"filters": [{"path": "value.selection", "op": "in", "value": ["home", "draw"]}]}
    assert eval_conditions(cond, RESULT_INLINE) is True
    cond_neg = {"filters": [{"path": "value.selection", "op": "in", "value": ["away"]}]}
    assert eval_conditions(cond_neg, RESULT_INLINE) is False


def test_all_filters_and_semantics():
    """Two filters that both match → True; either failing → False."""
    cond_both = {"filters": [
        {"path": "value.delta_pct", "op": ">",  "value": 5},
        {"path": "value.selection", "op": "==", "value": "home"},
    ]}
    assert eval_conditions(cond_both, RESULT_INLINE) is True

    cond_second_fails = {"filters": [
        {"path": "value.delta_pct", "op": ">",  "value": 5},
        {"path": "value.selection", "op": "==", "value": "away"},
    ]}
    assert eval_conditions(cond_second_fails, RESULT_INLINE) is False


def test_strength_path_in_filter():
    """`strength` is a valid path (not just strength_min shortcut)."""
    cond = {"filters": [{"path": "strength", "op": ">=", "value": 0.7}]}
    assert eval_conditions(cond, RESULT_INLINE) is True


def test_unknown_path_fails_closed():
    """Unknown path prefix → False, not raise."""
    cond = {"filters": [{"path": "secret.field", "op": "==", "value": 1}]}
    assert eval_conditions(cond, RESULT_INLINE) is False


def test_nested_value_path_not_supported_v1():
    """v1 explicitly does NOT support value.foo.bar — fail closed."""
    rep = {"strength": 0.8, "value": {"foo": {"bar": 1}}}
    cond = {"filters": [{"path": "value.foo.bar", "op": "==", "value": 1}]}
    assert eval_conditions(cond, rep) is False


def test_unknown_op_fails_closed():
    cond = {"filters": [{"path": "value.delta_pct", "op": "BETWEEN", "value": [5, 10]}]}
    assert eval_conditions(cond, RESULT_INLINE) is False


def test_op_on_missing_field_returns_false():
    """`value.absent > 5` → False (not raise)."""
    cond = {"filters": [{"path": "value.absent", "op": ">", "value": 5}]}
    assert eval_conditions(cond, RESULT_INLINE) is False


def test_op_with_none_strength_returns_false():
    cond = {"filters": [{"path": "strength", "op": ">", "value": 0.3}]}
    assert eval_conditions(cond, {"strength": None, "value": {}}) is False


def test_corrupted_value_json_treated_as_empty():
    """Garbage value_json → value{}, filters fail closed."""
    rep = {"strength": 0.8, "value_json": "not json {{{{ "}
    cond = {"filters": [{"path": "value.delta_pct", "op": ">", "value": 0}]}
    assert eval_conditions(cond, rep) is False


def test_non_dict_conditions_fails_closed():
    assert eval_conditions("oops", RESULT_INLINE) is False    # type: ignore[arg-type]
    assert eval_conditions(None, RESULT_INLINE) is False      # type: ignore[arg-type]
    assert eval_conditions([], RESULT_INLINE) is False        # type: ignore[arg-type]


def test_filter_with_non_dict_entry_fails_closed():
    cond = {"filters": ["not a dict"]}
    assert eval_conditions(cond, RESULT_INLINE) is False


def test_filter_eq_handles_type_mismatch_via_python_eq():
    """str == int → False (Python ==), not raise."""
    cond = {"filters": [{"path": "value.delta_pct", "op": "==", "value": "9.2"}]}
    assert eval_conditions(cond, RESULT_INLINE) is False
