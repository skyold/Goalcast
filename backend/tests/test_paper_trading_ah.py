"""Phase B (paper-trading-realism PRD) — AH settlement pure function.

`settle_ah(line, score_home, score_away, side, stake_units, entry_odds)` grades
an Asian Handicap bet given the FT score. No DB, no I/O — just math.

Covered grid:
  line ∈ {0, ±0.25, ±0.5, ±0.75, ±1}
  side ∈ {home, away}
  outcomes ∈ {win, loss, push, half_win, half_loss}
  pnl signed correctly for each outcome at stake_units=1.0, entry_odds=2.0
"""
from __future__ import annotations

import pytest

from services.paper_trading_ah import settle_ah


# ---------- integer / half lines (no quarter) ----------

@pytest.mark.parametrize(
    "line, score_h, score_a, side, expected_outcome, expected_pnl",
    [
        # line = 0 (平手盘) — push possible on draws
        ( 0.0, 1, 0, "home", "win",  +1.0),
        ( 0.0, 0, 0, "home", "push",  0.0),
        ( 0.0, 0, 1, "home", "loss", -1.0),
        ( 0.0, 0, 1, "away", "win",  +1.0),
        ( 0.0, 0, 0, "away", "push",  0.0),
        ( 0.0, 1, 0, "away", "loss", -1.0),

        # line = -0.5 (side gives 0.5 — must win outright)
        (-0.5, 1, 0, "home", "win",  +1.0),
        (-0.5, 2, 1, "home", "win",  +1.0),
        (-0.5, 0, 0, "home", "loss", -1.0),
        (-0.5, 1, 1, "home", "loss", -1.0),
        (-0.5, 0, 1, "home", "loss", -1.0),
        (-0.5, 0, 1, "away", "win",  +1.0),
        (-0.5, 1, 2, "away", "win",  +1.0),
        (-0.5, 0, 0, "away", "loss", -1.0),
        (-0.5, 1, 1, "away", "loss", -1.0),
        (-0.5, 1, 0, "away", "loss", -1.0),

        # line = +0.5 (side gets 0.5 — draw cashes)
        ( 0.5, 1, 0, "home", "win",  +1.0),
        ( 0.5, 0, 0, "home", "win",  +1.0),
        ( 0.5, 0, 1, "home", "loss", -1.0),
        ( 0.5, 1, 2, "home", "loss", -1.0),
        ( 0.5, 0, 1, "away", "win",  +1.0),
        ( 0.5, 0, 0, "away", "win",  +1.0),
        ( 0.5, 1, 0, "away", "loss", -1.0),

        # line = -1.0 (side must win by 2+; push at 1-goal win)
        (-1.0, 2, 0, "home", "win",  +1.0),
        (-1.0, 1, 0, "home", "push",  0.0),
        (-1.0, 0, 0, "home", "loss", -1.0),
        (-1.0, 1, 1, "home", "loss", -1.0),
        (-1.0, 0, 1, "home", "loss", -1.0),

        # line = +1.0 (side gets 1.0 — loss only if loses by 2+)
        ( 1.0, 1, 0, "home", "win",  +1.0),
        ( 1.0, 0, 0, "home", "win",  +1.0),
        ( 1.0, 0, 1, "home", "push",  0.0),
        ( 1.0, 1, 2, "home", "push",  0.0),
        ( 1.0, 0, 2, "home", "loss", -1.0),
    ],
)
def test_settle_ah_half_lines(line, score_h, score_a, side, expected_outcome, expected_pnl):
    outcome, pnl = settle_ah(line, score_h, score_a, side,
                              stake_units=1.0, entry_odds=2.0)
    assert outcome == expected_outcome
    assert pnl == pytest.approx(expected_pnl, abs=1e-9)


# ---------- quarter lines ----------

@pytest.mark.parametrize(
    "line, score_h, score_a, side, expected_outcome, expected_pnl",
    [
        # line = -0.25  (split: 0 / -0.5)
        (-0.25, 1, 0, "home", "win",       +1.0),
        (-0.25, 0, 0, "home", "half_loss", -0.5),
        (-0.25, 1, 1, "home", "half_loss", -0.5),
        (-0.25, 0, 1, "home", "loss",      -1.0),
        (-0.25, 0, 1, "away", "win",       +1.0),
        (-0.25, 0, 0, "away", "half_loss", -0.5),
        (-0.25, 1, 0, "away", "loss",      -1.0),

        # line = +0.25  (split: 0 / +0.5)
        ( 0.25, 1, 0, "home", "win",       +1.0),
        ( 0.25, 0, 0, "home", "half_win",  +0.5),
        ( 0.25, 1, 1, "home", "half_win",  +0.5),
        ( 0.25, 0, 1, "home", "loss",      -1.0),
        ( 0.25, 0, 1, "away", "win",       +1.0),
        ( 0.25, 0, 0, "away", "half_win",  +0.5),

        # line = -0.75  (split: -0.5 / -1.0)
        (-0.75, 2, 0, "home", "win",       +1.0),
        (-0.75, 1, 0, "home", "half_win",  +0.5),
        (-0.75, 0, 0, "home", "loss",      -1.0),
        (-0.75, 1, 1, "home", "loss",      -1.0),

        # line = +0.75  (split: +0.5 / +1.0)
        ( 0.75, 1, 0, "home", "win",       +1.0),
        ( 0.75, 0, 0, "home", "win",       +1.0),
        ( 0.75, 0, 1, "home", "half_loss", -0.5),
        ( 0.75, 1, 2, "home", "half_loss", -0.5),
        ( 0.75, 0, 2, "home", "loss",      -1.0),
    ],
)
def test_settle_ah_quarter_lines(line, score_h, score_a, side, expected_outcome, expected_pnl):
    outcome, pnl = settle_ah(line, score_h, score_a, side,
                              stake_units=1.0, entry_odds=2.0)
    assert outcome == expected_outcome
    assert pnl == pytest.approx(expected_pnl, abs=1e-9)


# ---------- pnl scales with stake and odds ----------

def test_settle_ah_pnl_scales_with_stake():
    """Win pnl = stake * (odds-1); loss pnl = -stake."""
    win_outcome, win_pnl = settle_ah(0.0, 1, 0, "home", stake_units=5.0, entry_odds=2.10)
    assert win_outcome == "win"
    assert win_pnl == pytest.approx(5.0 * (2.10 - 1), abs=1e-9)

    loss_outcome, loss_pnl = settle_ah(0.0, 0, 1, "home", stake_units=3.0, entry_odds=2.10)
    assert loss_outcome == "loss"
    assert loss_pnl == pytest.approx(-3.0, abs=1e-9)


def test_settle_ah_half_outcomes_use_half_stake():
    """half_win pnl = 0.5 * stake * (odds-1); half_loss pnl = -0.5 * stake."""
    hw_outcome, hw_pnl = settle_ah(0.25, 0, 0, "home", stake_units=4.0, entry_odds=2.50)
    assert hw_outcome == "half_win"
    assert hw_pnl == pytest.approx(0.5 * 4.0 * (2.50 - 1), abs=1e-9)

    hl_outcome, hl_pnl = settle_ah(-0.25, 0, 0, "home", stake_units=4.0, entry_odds=2.50)
    assert hl_outcome == "half_loss"
    assert hl_pnl == pytest.approx(-0.5 * 4.0, abs=1e-9)


# ---------- validation ----------

def test_settle_ah_rejects_invalid_side():
    with pytest.raises(ValueError):
        settle_ah(0.0, 1, 0, "draw", stake_units=1.0, entry_odds=2.0)


def test_settle_ah_rejects_nonpositive_stake_or_odds():
    with pytest.raises(ValueError):
        settle_ah(0.0, 1, 0, "home", stake_units=0.0, entry_odds=2.0)
    with pytest.raises(ValueError):
        settle_ah(0.0, 1, 0, "home", stake_units=1.0, entry_odds=0.0)
