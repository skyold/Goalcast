"""Asian Handicap outcome parsing + main-line derivation."""
import re

_RE = re.compile(r"^(home|away)_(?:(m|p)?(\d+))$")


def make_ah_outcome(side: str, line: float) -> str:
    """Build the OA-native outcome string for an AH bet on `side` at signed
    `line` (from side perspective). Inverse of `parse_ah_outcome_line`.

    Examples:
        make_ah_outcome('home', 0.0)   → 'home_0'
        make_ah_outcome('home', -0.5)  → 'home_m05'
        make_ah_outcome('away', 0.25)  → 'away_p025'
        make_ah_outcome('home', -1.25) → 'home_m125'

    Raises ValueError on unsupported fractional component (only 0 / 0.25 /
    0.5 / 0.75 are valid for AH).
    """
    if side not in ("home", "away"):
        raise ValueError(f"side must be 'home' or 'away', got {side!r}")
    if line == 0:
        return f"{side}_0"
    sign = "p" if line > 0 else "m"
    abs_line = abs(line)
    whole = int(abs_line)
    frac = round(abs_line - whole, 4)
    if frac == 0:
        digits = str(whole)
    elif frac == 0.5:
        digits = f"{whole}5"
    elif frac == 0.25:
        digits = f"{whole}25"
    elif frac == 0.75:
        digits = f"{whole}75"
    else:
        raise ValueError(f"Unsupported AH fractional line: {line}")
    return f"{side}_{sign}{digits}"


def parse_ah_outcome_line(outcome: str) -> tuple[str, float] | None:
    """'home_m05' -> ('home', -0.5);  'away_p075' -> ('away', 0.75);
       'home_0'   -> ('home', 0.0);   anything else -> None."""
    m = _RE.match(outcome)
    if not m:
        return None
    side, sign, digits = m.group(1), m.group(2), m.group(3)
    if digits == "0":
        return side, 0.0
    if len(digits) == 1:
        raw = float(digits)
    elif len(digits) == 2:
        raw = float(digits[0]) + (0.5 if digits[1] == "5" else 0.0)
    elif len(digits) == 3:
        # '075' -> 0.75;  '125' -> 1.25
        raw = float(digits[0]) + float(digits[1:]) / 100
    else:
        return None
    sign_val = -1 if sign == "m" else 1
    return side, sign_val * raw


def derive_main_ah_line(rows: list[dict], bookmaker_id: int) -> tuple[float, float, float] | None:
    """Return (line, home_odds, away_odds) for the AH line whose two-side odds are
    closest to each other for the given bookmaker. `line` is from home perspective."""
    buckets: dict[float, dict[str, float]] = {}
    for r in rows:
        if r.get("bookmaker_id") != bookmaker_id or r.get("market_id") != 51:
            continue
        parsed = parse_ah_outcome_line(r.get("outcome", ""))
        if parsed is None:
            continue
        side, line = parsed
        home_line = line if side == "home" else -line
        b = buckets.setdefault(home_line, {})
        odds = r.get("current") or 0
        try:
            o = float(odds)
        except (TypeError, ValueError):
            continue
        b[side] = o
    candidates = [
        (ln, b["home"], b["away"])
        for ln, b in buckets.items()
        if "home" in b and "away" in b and b["home"] > 0 and b["away"] > 0
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda t: abs(t[1] - t[2]))
