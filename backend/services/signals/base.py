"""Goalcast Signals — abstract interface + registry.

Each signal is a Pure Function:
    compute(db, fixture_id, waypoint) -> dict | None

Reads ONLY from waypoint-stamped historical tables (historical_predictions /
historical_odds / fixtures), NEVER from upsert tables (predictions /
bookmaker_odds). See docs/PRD/proprietary-signals.prd.md 信号读源契约.

Signals registered in REGISTERED are invoked by services/snapshot.py after
historical_* rows for (fixture, waypoint) are written.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import aiosqlite


class BaseSignal(ABC):
    """Stateless signal computer. Subclasses set the ClassVar metadata
    fields and implement compute().

    Metadata split:
      - signal_type / signal_version / scope    — runtime identifiers (load-bearing)
      - description / output_schema /
        strength_formula / failure_modes        — user-facing catalog metadata
        (consumed by /api/signals/catalog,
         rendered next to methodology markdown)
    """

    # Runtime identifiers.
    signal_type: ClassVar[str]      # stable English ID, e.g. 'GS-Mispricing'
    signal_version: ClassVar[str]   # semver-ish, e.g. 'v1.0'
    scope: ClassVar[str]            # 'public' | 'member'

    # User-facing catalog metadata. Defaults are intentionally empty so that
    # the abstract base + existing concrete signals continue to import; each
    # subclass SHOULD override these to populate the catalog endpoint.
    description: ClassVar[str] = ""               # one-line zh summary, ≤ 60 chars
    output_schema: ClassVar[dict[str, str]] = {}  # field → "type, semantics" doc
    strength_formula: ClassVar[str] = ""          # human-readable strength normalisation
    failure_modes: ClassVar[list[str]] = []       # short bullets of "returns None when ..."

    @abstractmethod
    async def compute(
        self,
        db: aiosqlite.Connection,
        fixture_id: int,
        waypoint: str,
    ) -> dict | None:
        """Return {'value_json': str, 'strength': float} or None if inputs missing.

        strength: normalized [0, 1] for cross-signal ranking. Callers treat None
        as "no signal" — do not coerce.
        """
        ...


REGISTERED: list[BaseSignal] = []


def register(cls: type[BaseSignal]) -> type[BaseSignal]:
    """Decorator: instantiate and add to REGISTERED. Use on every concrete signal."""
    REGISTERED.append(cls())
    return cls
