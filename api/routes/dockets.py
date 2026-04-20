"""Docket discovery endpoint — list available dockets with comment counts."""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.models.dockets import DocketListResponse, DocketOut
from db.queries import count_dockets, list_dockets

router = APIRouter(prefix="/dockets", tags=["dockets"])


@router.get("", response_model=DocketListResponse)
def list_available_dockets(
    q: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> DocketListResponse:
    """Return available dockets ordered by comment volume.

    Optionally filter by case-insensitive substring match on docket ID.
    Useful for autocomplete: supply ``q`` with a partial docket ID.
    """
    rows = list_dockets(db, q=q, limit=limit, offset=offset)
    total = count_dockets(db, q=q)
    return DocketListResponse(
        items=[DocketOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
