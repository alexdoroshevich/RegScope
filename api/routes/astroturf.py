"""Astroturf detection endpoints — duplicate groups and summary."""

from __future__ import annotations

from typing import Annotated

import duckdb  # noqa: TC002 — runtime-required for FastAPI annotation resolution
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.models.astroturf import (
    AstroturfSummaryResponse,
    DuplicateGroupListResponse,
    DuplicateGroupOut,
)
from db.queries import get_astroturf_summary, get_duplicate_groups

router = APIRouter(prefix="/astroturf", tags=["astroturf"])


@router.get("/groups", response_model=DuplicateGroupListResponse)
def list_duplicate_groups(
    astroturf_only: bool = False,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> DuplicateGroupListResponse:
    """Return duplicate comment groups, optionally filtered to astroturf."""
    rows = get_duplicate_groups(db, astroturf_only=astroturf_only, limit=limit, offset=offset)
    return DuplicateGroupListResponse(
        items=[DuplicateGroupOut.model_validate(r) for r in rows],
        limit=limit,
        offset=offset,
    )


@router.get("/summary", response_model=AstroturfSummaryResponse)
def astroturf_summary(
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> AstroturfSummaryResponse:
    """Return overall astroturf detection statistics."""
    stats = get_astroturf_summary(db)
    return AstroturfSummaryResponse.model_validate(stats)
