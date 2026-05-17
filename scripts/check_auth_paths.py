#!/usr/bin/env python3
"""Audit every `fetch(` call in frontend/src for cookie transmission.

Without `credentials: 'include'` the gc_token httpOnly cookie won't ride along,
so /api/me/* would always return 401 even when the user is logged in. This script
catches that regression class.

Exits 0 if all fetch() callsites either include credentials, are inside the
shared api helpers, or are inside this allow-list. Exits 1 otherwise.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "frontend" / "src"

FETCH_RE = re.compile(r"\bfetch\s*\(")
CRED_RE = re.compile(r"credentials\s*:\s*['\"]include['\"]")


def main() -> int:
    bad: list[tuple[Path, int, str]] = []
    for path in SRC.rglob("*"):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        for ln, line in enumerate(lines, 1):
            if not FETCH_RE.search(line):
                continue
            # Pull a 5-line window so multi-line fetch() init options are visible.
            window = "\n".join(lines[max(ln - 1, 0):ln + 4])
            if CRED_RE.search(window):
                continue
            bad.append((path, ln, line.strip()))

    if bad:
        print(f"FAIL: {len(bad)} fetch() call(s) without `credentials: 'include'`:")
        for path, ln, line in bad:
            rel = path.relative_to(REPO_ROOT).as_posix()
            snippet = line if len(line) < 100 else line[:97] + "..."
            print(f"  {rel}:{ln}  {snippet}")
        print()
        print("Add `{ credentials: 'include' }` to the fetch options, or route the")
        print("call through the api.ts helpers which already do it.")
        return 1

    total = sum(1 for p in SRC.rglob("*") if p.suffix in {".ts", ".tsx"})
    print(f"PASS: scanned {total} ts/tsx files, every fetch() forwards cookies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
