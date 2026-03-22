import re
from typing import List, Dict, Any, Optional
from src.aggregator.schema import OddsData
from src.utils.logger import logger


def parse_lineup(text: str) -> List[str]:
    if not text or not text.strip():
        return []

    lines = text.strip().split("\n")
    players = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"[,;|]\s*", line)
        for part in parts:
            cleaned = re.sub(r"^\d+[\.\)]\s*", "", part.strip())
            cleaned = re.sub(r"\s*\(.*?\)", "", cleaned)
            cleaned = cleaned.strip()

            if cleaned and len(cleaned) > 1 and len(cleaned) < 50:
                players.append(cleaned)

    return players


def parse_injuries(text: str) -> List[Dict[str, str]]:
    if not text or not text.strip():
        return []

    injuries = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = re.split(r"[,;|]\s*", line)
        for part in parts:
            part = part.strip()
            if not part:
                continue

            severity = "unknown"
            if any(kw in part.lower() for kw in ["doubt", "doubtful", "?", "存疑"]):
                severity = "doubtful"
            elif any(kw in part.lower() for kw in ["out", "injured", "缺阵", "伤"]):
                severity = "out"

            name = re.sub(r"\s*\(.*?\)", "", part)
            name = re.sub(
                r"\b(doubtful|out|injured|doubt|缺阵|伤|存疑)\b", "", name, flags=re.IGNORECASE
            ).strip()

            if name:
                injuries.append({"name": name, "severity": severity})

    return injuries


def parse_odds(text: str) -> Optional[OddsData]:
    if not text or not text.strip():
        return None

    text = text.strip()

    home = None
    draw = None
    away = None

    patterns = [
        r"(?:home|主|h)[^\d]*([\d.]+)",
        r"(?:draw|平|d)[^\d]*([\d.]+)",
        r"(?:away|客|a)[^\d]*([\d.]+)",
    ]

    home_match = re.search(patterns[0], text.lower())
    draw_match = re.search(patterns[1], text.lower())
    away_match = re.search(patterns[2], text.lower())

    if home_match:
        try:
            home = float(home_match.group(1))
        except ValueError:
            pass

    if draw_match:
        try:
            draw = float(draw_match.group(1))
        except ValueError:
            pass

    if away_match:
        try:
            away = float(away_match.group(1))
        except ValueError:
            pass

    if home and draw and away:
        return OddsData(
            current_home=home,
            current_draw=draw,
            current_away=away,
        )

    numbers = re.findall(r"(\d+\.?\d*)", text)
    if len(numbers) >= 3:
        try:
            return OddsData(
                current_home=float(numbers[0]),
                current_draw=float(numbers[1]),
                current_away=float(numbers[2]),
            )
        except ValueError:
            pass

    return None
