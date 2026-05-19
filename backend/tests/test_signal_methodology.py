"""Phase 0 tests — BaseSignal catalog metadata + signal_methodology table +
seed script idempotency + REGISTERED coverage check.

Locks in three guarantees:
1. BaseSignal exposes 4 new ClassVars with safe empty defaults.
2. Every registered signal overrides those 4 ClassVars with non-empty content
   (catch silent regression where someone adds a new signal but forgets
   methodology).
3. seed_methodology() is idempotent and content-preserving across reruns.
"""
from __future__ import annotations

import aiosqlite
import pytest


@pytest.mark.asyncio
async def test_base_signal_has_catalog_metadata_defaults():
    from services.signals.base import BaseSignal
    # Defaults exist so abstract base and forgetful subclasses still import.
    assert BaseSignal.description == ""
    assert BaseSignal.output_schema == {}
    assert BaseSignal.strength_formula == ""
    assert BaseSignal.failure_modes == []


@pytest.mark.asyncio
async def test_every_registered_signal_has_non_empty_metadata():
    """Coverage guard: adding a new signal without methodology must fail CI."""
    from services.signals import REGISTERED
    assert len(REGISTERED) > 0, "REGISTERED is empty — signal package not loaded"
    for sig in REGISTERED:
        ctx = f"signal {sig.signal_type}"
        assert sig.description, f"{ctx}: description empty"
        assert len(sig.description) <= 80, f"{ctx}: description > 80 chars"
        assert sig.output_schema, f"{ctx}: output_schema empty"
        assert sig.strength_formula, f"{ctx}: strength_formula empty"
        assert sig.failure_modes, f"{ctx}: failure_modes empty"


@pytest.mark.asyncio
async def test_signal_methodology_table_exists_after_init():
    """signal_methodology table is created by init_db (idempotent)."""
    from database import _db_path, init_db
    await init_db()
    async with aiosqlite.connect(_db_path()) as db:
        async with db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='signal_methodology'"
        ) as cur:
            row = await cur.fetchone()
    assert row is not None, "signal_methodology table missing after init_db"


@pytest.mark.asyncio
async def test_seed_methodology_writes_rows_for_all_registered():
    """Seed produces zh + en row for every registered signal_type."""
    from scripts.seed_methodology import seed_methodology
    from services.signals import REGISTERED
    from database import _db_path
    await seed_methodology()
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT signal_type, locale FROM signal_methodology"
        ) as cur:
            rows = [(r["signal_type"], r["locale"]) for r in await cur.fetchall()]
    by_type: dict[str, set[str]] = {}
    for st, loc in rows:
        by_type.setdefault(st, set()).add(loc)
    for sig in REGISTERED:
        ctx = f"signal {sig.signal_type}"
        assert sig.signal_type in by_type, f"{ctx}: no methodology rows seeded"
        assert {"zh", "en"} <= by_type[sig.signal_type], f"{ctx}: missing zh or en"


@pytest.mark.asyncio
async def test_seed_methodology_is_idempotent():
    """Running seed twice produces same row count, body_md preserved, updated_at refreshed."""
    from scripts.seed_methodology import seed_methodology
    from database import _db_path
    await seed_methodology()
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) AS n FROM signal_methodology") as cur:
            n1 = (await cur.fetchone())["n"]
        async with db.execute(
            """SELECT signal_type, locale, body_md, updated_at
               FROM signal_methodology
               WHERE signal_type='GS-Mispricing' AND locale='zh'"""
        ) as cur:
            r1 = dict(await cur.fetchone())
    # Second run should not duplicate rows, should refresh updated_at,
    # and body_md must be byte-identical (no double-escaping etc.).
    await seed_methodology()
    async with aiosqlite.connect(_db_path()) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT COUNT(*) AS n FROM signal_methodology") as cur:
            n2 = (await cur.fetchone())["n"]
        async with db.execute(
            """SELECT body_md, updated_at FROM signal_methodology
               WHERE signal_type='GS-Mispricing' AND locale='zh'"""
        ) as cur:
            r2 = dict(await cur.fetchone())
    assert n1 == n2, "seed re-run duplicated rows"
    assert r1["body_md"] == r2["body_md"], "body_md changed across re-run"
    # updated_at re-runs to a new ISO timestamp; just assert it didn't go backwards.
    assert r2["updated_at"] >= r1["updated_at"]


@pytest.mark.asyncio
async def test_methodology_body_contains_expected_section_headings():
    """Sanity: each seeded body has the canonical sections used by the UI."""
    from scripts.seed_methodology import METHODOLOGY
    for signal_type, locales in METHODOLOGY.items():
        for locale, body_md in locales.items():
            ctx = f"{signal_type}/{locale}"
            # zh uses '计算原理', en uses 'How it computes'
            assert ("## 计算原理" in body_md) or ("## How it computes" in body_md), \
                f"{ctx}: missing canonical opening section"
