def compute_edge(prob: float | None, odds: float | None) -> float | None:
    if prob is None or odds is None or odds <= 0:
        return None
    return round((prob - 1.0 / odds) * 100, 2)
