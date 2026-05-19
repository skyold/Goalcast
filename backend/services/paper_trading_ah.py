"""Asian Handicap settlement — pure function for AH bet grading.

Phase B of docs/PRD/paper-trading-realism.prd.md. No DB, no I/O — composes
into services.paper_trading.settle_bets() via a market_id dispatcher.

Quarter-line (±0.25, ±0.75, ...) bets are settled as two equal half-stake
bets on the adjacent integer/half lines (standard real-bookmaker rule):
    line = L  →  half stake at L-0.25  +  half stake at L+0.25
Adjacent half-lines can never produce a (win, loss) combo for an integer
score, so the only meaningful quarter-line composites are:
    {win, win}    → 'win'
    {loss, loss}  → 'loss'
    {win, push}   → 'half_win'
    {loss, push}  → 'half_loss'
"""
from __future__ import annotations


_ALLOWED_SIDES = ("home", "away")


def _settle_half_line(
    line: float,
    score_home: int,
    score_away: int,
    side: str,
) -> str:
    """Grade a single integer/half line. Returns 'win', 'loss', or 'push'."""
    if side == "home":
        side_goals, opp_goals = score_home, score_away
    else:
        side_goals, opp_goals = score_away, score_home
    adj = side_goals + line - opp_goals
    if adj > 0:
        return "win"
    if adj < 0:
        return "loss"
    return "push"


def _is_quarter_line(line: float) -> bool:
    """True iff line ∈ {..., ±0.25, ±0.75, ±1.25, ...}."""
    return round(line * 4) % 2 != 0


def settle_ah(
    line: float,
    score_home: int,
    score_away: int,
    side: str,
    stake_units: float,
    entry_odds: float,
) -> tuple[str, float]:
    """Grade an Asian Handicap bet. Returns ``(outcome, pnl_units)``.

    Parameters
    ----------
    line : float
        Handicap signed from the bet's ``side`` perspective:
          side='home', line=-0.5  ↔ "home -0.5" (home gives 0.5 to away)
          side='away', line=+0.5  ↔ "away +0.5" (away gets 0.5)
    side : str
        'home' or 'away'.
    stake_units, entry_odds : float
        Both must be > 0. Decimal odds convention (entry_odds=2.0 ↔ +100).

    Outcomes
    --------
    'win'        — full stake wins  → pnl = +stake * (odds-1)
    'loss'       — full stake loses → pnl = -stake
    'push'       — full refund      → pnl = 0
    'half_win'   — half wins, half refunds  → pnl = +0.5 * stake * (odds-1)
    'half_loss'  — half loses, half refunds → pnl = -0.5 * stake
    """
    if side not in _ALLOWED_SIDES:
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")
    if stake_units <= 0:
        raise ValueError(f"stake_units must be positive, got {stake_units!r}")
    if entry_odds <= 0:
        raise ValueError(f"entry_odds must be positive, got {entry_odds!r}")

    if not _is_quarter_line(line):
        r = _settle_half_line(line, score_home, score_away, side)
        if r == "win":
            return ("win", stake_units * (entry_odds - 1))
        if r == "loss":
            return ("loss", -stake_units)
        return ("push", 0.0)

    lower = line - 0.25
    upper = line + 0.25
    r_lower = _settle_half_line(lower, score_home, score_away, side)
    r_upper = _settle_half_line(upper, score_home, score_away, side)

    half_stake = stake_units / 2.0

    def _half_pnl(r: str) -> float:
        if r == "win":
            return half_stake * (entry_odds - 1)
        if r == "loss":
            return -half_stake
        return 0.0

    pnl = _half_pnl(r_lower) + _half_pnl(r_upper)
    outcomes = {r_lower, r_upper}
    if outcomes == {"win"}:
        return ("win", pnl)
    if outcomes == {"loss"}:
        return ("loss", pnl)
    if outcomes == {"win", "push"}:
        return ("half_win", pnl)
    if outcomes == {"loss", "push"}:
        return ("half_loss", pnl)
    raise AssertionError(
        f"impossible quarter-line outcome combo lower={r_lower!r} upper={r_upper!r} "
        f"(line={line}, score={score_home}-{score_away}, side={side})"
    )
