"""Astroturf detection endpoints — duplicate groups and summary."""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_db
from api.models.astroturf import (
    AstroturfSummaryResponse,
    DuplicateGroupListResponse,
    DuplicateGroupOut,
    GroupCommentOut,
)
from db.queries import (
    count_duplicate_groups,
    get_astroturf_summary,
    get_comments_by_group,
    get_duplicate_groups,
)

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
    total = count_duplicate_groups(db, astroturf_only=astroturf_only)
    return DuplicateGroupListResponse(
        items=[DuplicateGroupOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/groups/{group_id}/comments", response_model=list[GroupCommentOut])
def list_group_comments(
    group_id: int,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> list[GroupCommentOut]:
    """Return the actual comments belonging to a duplicate group."""
    rows = get_comments_by_group(db, group_id, limit=limit)
    if not rows:
        # Distinguish "group exists but has no matched comments" from "group not found"
        exists = db.execute(
            "SELECT 1 FROM duplicate_groups WHERE group_id = ?", [group_id]
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=404, detail=f"Group {group_id} not found")
    return [GroupCommentOut.model_validate(r) for r in rows]


@router.get("/summary", response_model=AstroturfSummaryResponse)
def astroturf_summary(
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> AstroturfSummaryResponse:
    """Return overall astroturf detection statistics."""
    stats = get_astroturf_summary(db)
    return AstroturfSummaryResponse.model_validate(stats)
