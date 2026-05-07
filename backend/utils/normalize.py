# backend/utils/normalize.py
import re
import unicodedata


def normalize_team_name(name: str) -> str:
    """移除重音、空格、连字符，全部小写，用于跨 provider 队名比较。"""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_str.lower())
