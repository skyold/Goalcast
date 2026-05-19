"""Paper-trading endpoints — Book CRUD + read-side summaries.

Surfaces:
  GET    /paper-trading/house       — legacy single-band aggregate
  GET    /paper-trading/books       — Phase 4b multi-Book list with summary
  POST   /paper-trading/books       — Phase 4c create Personal Book (or fork)
  PATCH  /paper-trading/books/:id   — Phase 4c edit Personal Book
  DELETE /paper-trading/books/:id   — Phase 4c soft-archive Personal Book

Invariants (server-enforced):
  - House Books (user_id=0) are immutable via POST/PATCH/DELETE — they are
    created/migrated by services/signals/books.bootstrap_books at startup
    only. Any user attempt to mutate user_id=0 → 403.
  - Personal Books have user_id = current_user.id and match_scope ∈
    {'all', 'my_leagues'}. Other users' books are invisible (404 on probe).
  - DELETE is soft (sets archived_at). Pending bets continue to settle;
    new bets stop because place_bets_for_books filters archived_at IS NULL.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

import aiosqlite
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi import status as http_status

from database import get_db
from services import paper_trading as pt_svc
from services.auth import get_current_user_optional

router = APIRouter()

_ALLOWED_MATCH_SCOPES = {"all", "my_leagues"}
_HOUSE_USER_ID = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _require_user(user: Optional[dict]) -> dict:
    if user is None:
        raise HTTPException(status_code=401, detail="login required")
    return user


def _validate_conditions(raw: Any) -> dict:
    """Conditions must be a JSON object; structural validation deferred to
    services.signals.conditions.eval_conditions which fails closed on bad
    input. Here we just gate the shape."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=422, detail="conditions must be an object")
    return raw


def _validate_match_scope(scope: Any, *, default: str) -> str:
    if scope is None:
        return default
    if scope not in _ALLOWED_MATCH_SCOPES:
        raise HTTPException(status_code=422, detail="match_scope must be 'all' or 'my_leagues'")
    return scope


def _validate_starting_units(units: Any, *, default: float) -> float:
    if units is None:
        return default
    try:
        u = float(units)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="starting_units must be a number")
    if u <= 0 or u > 1_000_000:
        raise HTTPException(status_code=422, detail="starting_units out of range (0, 1e6]")
    return u


def _serialize_book(row: dict, summary: Optional[dict] = None) -> dict:
    try:
        conditions = json.loads(row["conditions_json"]) if row["conditions_json"] else {}
    except (TypeError, ValueError):
        conditions = {}
    return {
        "id":             row["id"],
        "user_id":        row["user_id"],
        "name":           row["name"],
        "signal_type":    row["signal_type"],
        "signal_version": row["signal_version"],
        "conditions":     conditions,
        "starting_units": row["starting_units"],
        "match_scope":    row["match_scope"],
        "scope":          "house" if row["user_id"] == _HOUSE_USER_ID else "personal",
        "created_at":     row["created_at"],
        "archived_at":    row["archived_at"],
        "summary":        summary,
    }


async def _fetch_book(db: aiosqlite.Connection, book_id: int) -> Optional[dict]:
    async with db.execute(
        """SELECT id, user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope,
                  created_at, archived_at
           FROM simulated_books WHERE id=?""",
        (book_id,),
    ) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


@router.get("/paper-trading/house")
async def get_house(
    book_type: Annotated[str, Query()] = "house_5pct",
    start_bankroll: Annotated[float, Query(gt=0, le=1_000_000)] = 1000.0,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await pt_svc.house_book_summary(
        db, book_type=book_type, start_bankroll=start_bankroll,
    )


@router.get("/paper-trading/books")
async def get_books(
    include_archived: Annotated[bool, Query()] = False,
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """List all visible Books with per-book summary metrics.

    Visibility:
      - Anonymous → only House Books (user_id=0)
      - Authenticated → House Books + that user's Personal Books

    Each item carries the static Book fields plus a `summary` block with
    settled/pending counts, current bankroll, ROI, win rate and the bankroll
    timeseries (oldest → newest). The frontend multi-curve ROI chart slices
    the summary.timeseries directly into a polyline.
    """
    where = "WHERE (user_id=0"
    params: list = []
    if user is not None:
        where += " OR user_id=?"
        params.append(user["id"])
    where += ")"
    if not include_archived:
        where += " AND archived_at IS NULL"

    async with db.execute(
        f"""SELECT id, user_id, name, signal_type, signal_version,
                   conditions_json, starting_units, match_scope,
                   created_at, archived_at
            FROM simulated_books {where}
            ORDER BY user_id ASC, id ASC""",
        params,
    ) as cur:
        rows = [dict(r) for r in await cur.fetchall()]

    items: list[dict] = []
    for r in rows:
        summary = await pt_svc.book_summary(
            db, book_id=r["id"], starting_units=r["starting_units"],
        )
        try:
            conditions = json.loads(r["conditions_json"]) if r["conditions_json"] else {}
        except (TypeError, ValueError):
            conditions = {}
        items.append({
            "id":             r["id"],
            "user_id":        r["user_id"],
            "name":           r["name"],
            "signal_type":    r["signal_type"],
            "signal_version": r["signal_version"],
            "conditions":     conditions,
            "starting_units": r["starting_units"],
            "match_scope":    r["match_scope"],
            "scope":          "house" if r["user_id"] == 0 else "personal",
            "created_at":     r["created_at"],
            "archived_at":    r["archived_at"],
            "summary":        summary,
        })
    return {"items": items, "count": len(items)}


@router.post("/paper-trading/books", status_code=http_status.HTTP_201_CREATED)
async def create_book(
    body: Annotated[dict, Body(...)] = ...,
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a Personal Book. Two construction paths:

    Fork:  body.fork_from = <house_book_id> → copy signal_type / version /
           conditions / starting_units; user can override conditions /
           starting_units / match_scope / name.
    Bare:  body.signal_type + body.signal_version explicitly; conditions
           default to {}; starting_units default 100.0.

    `name` is required and must be unique per user (UNIQUE(user_id, name)).
    """
    me = await _require_user(user)
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")

    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise HTTPException(status_code=422, detail="name is required")
    name = name.strip()
    if len(name) > 80:
        raise HTTPException(status_code=422, detail="name must be ≤ 80 chars")

    # Resolve template (fork) or explicit signal binding.
    signal_type:    Optional[str] = None
    signal_version: Optional[str] = None
    conditions:     dict = {}
    starting_units: float = 100.0

    fork_from = body.get("fork_from")
    if fork_from is not None:
        try:
            fork_id = int(fork_from)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="fork_from must be an integer book id")
        src = await _fetch_book(db, fork_id)
        if src is None:
            raise HTTPException(status_code=404, detail="fork_from book not found")
        signal_type    = src["signal_type"]
        signal_version = src["signal_version"]
        try:
            conditions = json.loads(src["conditions_json"]) if src["conditions_json"] else {}
        except (TypeError, ValueError):
            conditions = {}
        starting_units = src["starting_units"]
    else:
        signal_type    = body.get("signal_type")
        signal_version = body.get("signal_version")
        if not isinstance(signal_type, str) or not isinstance(signal_version, str):
            raise HTTPException(
                status_code=422,
                detail="provide fork_from OR (signal_type + signal_version)",
            )

    # Body overrides on top of fork / explicit binding.
    if "conditions" in body:
        conditions = _validate_conditions(body["conditions"])
    if "starting_units" in body:
        starting_units = _validate_starting_units(body["starting_units"], default=starting_units)
    match_scope = _validate_match_scope(body.get("match_scope"), default="my_leagues")

    now = _now()
    try:
        async with db.execute(
            """INSERT INTO simulated_books
                 (user_id, name, signal_type, signal_version,
                  conditions_json, starting_units, match_scope, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (me["id"], name, signal_type, signal_version,
             json.dumps(conditions, separators=(",", ":")),
             starting_units, match_scope, now),
        ) as cur:
            book_id = cur.lastrowid
        await db.commit()
    except aiosqlite.IntegrityError as e:
        # UNIQUE(user_id, name) collision.
        raise HTTPException(status_code=409, detail=f"name already taken: {e}")

    created = await _fetch_book(db, book_id)
    assert created is not None
    return _serialize_book(created)


@router.patch("/paper-trading/books/{book_id}")
async def update_book(
    book_id: int,
    body: Annotated[dict, Body(...)] = ...,
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update mutable fields of a Personal Book: name / conditions /
    starting_units / match_scope. signal_type and signal_version are
    immutable (use POST to create a new book if you want a different signal).
    """
    me = await _require_user(user)
    if not isinstance(body, dict):
        raise HTTPException(status_code=422, detail="body must be a JSON object")

    row = await _fetch_book(db, book_id)
    if row is None or row["user_id"] != me["id"]:
        # Don't leak existence of others' Books — same 404 for both cases.
        raise HTTPException(status_code=404, detail="book not found")
    if row["user_id"] == _HOUSE_USER_ID:
        # Defensive: House Books are user_id=0 so can never equal me["id"]>0
        # above, but spell out the invariant.
        raise HTTPException(status_code=403, detail="House Books are immutable")

    sets: list[str] = []
    params: list = []

    if "name" in body:
        new_name = body["name"]
        if not isinstance(new_name, str) or not new_name.strip():
            raise HTTPException(status_code=422, detail="name must be a non-empty string")
        new_name = new_name.strip()
        if len(new_name) > 80:
            raise HTTPException(status_code=422, detail="name must be ≤ 80 chars")
        sets.append("name=?")
        params.append(new_name)

    if "conditions" in body:
        conditions = _validate_conditions(body["conditions"])
        sets.append("conditions_json=?")
        params.append(json.dumps(conditions, separators=(",", ":")))

    if "starting_units" in body:
        units = _validate_starting_units(body["starting_units"], default=row["starting_units"])
        sets.append("starting_units=?")
        params.append(units)

    if "match_scope" in body:
        scope = _validate_match_scope(body["match_scope"], default=row["match_scope"])
        sets.append("match_scope=?")
        params.append(scope)

    if not sets:
        # No-op PATCH; just return the unmodified row.
        return _serialize_book(row)

    params.extend([book_id, me["id"]])
    try:
        await db.execute(
            f"UPDATE simulated_books SET {', '.join(sets)} "
            f"WHERE id=? AND user_id=?",
            params,
        )
        await db.commit()
    except aiosqlite.IntegrityError as e:
        raise HTTPException(status_code=409, detail=f"name already taken: {e}")

    updated = await _fetch_book(db, book_id)
    assert updated is not None
    return _serialize_book(updated)


@router.delete("/paper-trading/books/{book_id}", status_code=http_status.HTTP_200_OK)
async def archive_book(
    book_id: int,
    user: Optional[dict] = Depends(get_current_user_optional),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Soft-archive a Personal Book. Sets archived_at = now(); pending bets
    keep their book_id, settle_bets continues to process them, but
    place_bets_for_books stops placing new bets on this book (it filters
    archived_at IS NULL).

    Idempotent: archiving an already-archived book is a no-op (returns the
    row with the original archived_at preserved).
    """
    me = await _require_user(user)
    row = await _fetch_book(db, book_id)
    if row is None or row["user_id"] != me["id"]:
        raise HTTPException(status_code=404, detail="book not found")
    if row["user_id"] == _HOUSE_USER_ID:
        raise HTTPException(status_code=403, detail="House Books are immutable")

    if row["archived_at"] is None:
        await db.execute(
            "UPDATE simulated_books SET archived_at=? WHERE id=? AND user_id=?",
            (_now(), book_id, me["id"]),
        )
        await db.commit()

    updated = await _fetch_book(db, book_id)
    assert updated is not None
    return _serialize_book(updated)
