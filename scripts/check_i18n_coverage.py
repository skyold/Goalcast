#!/usr/bin/env python3
"""Scan frontend/src for hardcoded Chinese strings that should be in messages.zh.json.

Exits 0 if no unexpected leaks, 1 otherwise. Intended as a CI gate.

Allow-list policy:
- Files listed in `ALLOWED_FILES` are skipped (glossary, team metadata, data seeds,
  the i18n module itself, and tests/fixtures).
- Lines containing any string in `ALLOWED_INLINE_MARKERS` are skipped — used for
  the locale toggle button + the format.ts time-ago fallback which are designed
  to render both languages.

Run from repo root:
    python scripts/check_i18n_coverage.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "frontend" / "src"
MESSAGES_ZH = SRC / "lib" / "i18n" / "messages.zh.json"
MESSAGES_EN = SRC / "lib" / "i18n" / "messages.en.json"

# Skip these files entirely — they own Chinese content by design.
ALLOWED_FILES = {
    "lib/glossary.ts",
    "lib/teamMeta.ts",
    "lib/popularLeagues.ts",
    "lib/i18n/messages.zh.json",
    "lib/i18n/messages.en.json",
    "lib/i18n/index.ts",
}

# Lines containing these markers are intentional dual-language rendering and
# are part of the i18n design, not leaks.
ALLOWED_INLINE_MARKERS = (
    "Switch to English",       # toggle title (always both languages)
    "切换到中文",                # toggle title (always both languages)
    "locale === 'en' ?",       # format.ts ternary fallback by design
    "locale === 'zh' ? 'EN'",  # toggle button label
)

CJK_RE = re.compile(r"[一-鿿]+")


def main() -> int:
    if not MESSAGES_ZH.exists():
        print(f"FAIL: missing {MESSAGES_ZH.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1

    with MESSAGES_ZH.open(encoding="utf-8") as f:
        zh_msgs = json.load(f)
    with MESSAGES_EN.open(encoding="utf-8") as f:
        en_msgs = json.load(f)

    # Key-set drift: every zh key must have an en counterpart and vice versa.
    zh_keys = set(zh_msgs.keys())
    en_keys = set(en_msgs.keys())
    missing_in_en = sorted(zh_keys - en_keys)
    missing_in_zh = sorted(en_keys - zh_keys)
    if missing_in_en or missing_in_zh:
        print("FAIL: messages key drift")
        if missing_in_en:
            print(f"  zh has but en missing ({len(missing_in_en)}): {missing_in_en[:10]}{'...' if len(missing_in_en) > 10 else ''}")
        if missing_in_zh:
            print(f"  en has but zh missing ({len(missing_in_zh)}): {missing_in_zh[:10]}{'...' if len(missing_in_zh) > 10 else ''}")
        return 1

    leaks: list[tuple[Path, int, str]] = []
    for path in SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        rel = path.relative_to(SRC).as_posix()
        if rel in ALLOWED_FILES:
            continue
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not CJK_RE.search(line):
                continue
            if any(m in line for m in ALLOWED_INLINE_MARKERS):
                continue
            leaks.append((path, ln, line.strip()))

    if leaks:
        print(f"FAIL: {len(leaks)} hardcoded Chinese string(s) leaked outside i18n:")
        for path, ln, line in leaks:
            rel = path.relative_to(REPO_ROOT).as_posix()
            snippet = line if len(line) < 100 else line[:97] + "..."
            print(f"  {rel}:{ln}  {snippet}")
        print()
        print("Add the string to messages.zh.json + messages.en.json and switch the")
        print("callsite to `t('key')`, or extend ALLOWED_INLINE_MARKERS if intentional.")
        return 1

    print(f"PASS: {len(zh_keys)} keys, {sum(1 for _ in SRC.rglob('*.tsx'))} tsx files scanned, 0 leaks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
