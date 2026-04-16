"""Comment endpoints — list and count by docket."""

from __future__ import annotations

from typing import Annotated

import duckdb  # noqa: TC002 — runtime-required for FastAPI annotation resolution
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.models.comments import CommentListResponse, CommentOut
from db.queries import count_comments_by_docket, get_comments_by_docket

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/{docket_id}", response_model=CommentListResponse)
def list_comments(
    docket_id: str,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> CommentListResponse:
    """Return paginated comments for a docket."""
    rows = get_comments_by_docket(db, docket_id, limit=limit, offset=offset)
    total = count_comments_by_docket(db, docket_id)
    return CommentListResponse(
        items=[CommentOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
