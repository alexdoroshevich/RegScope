"""Cluster endpoints — list clusters and their comments by docket."""

from __future__ import annotations

from typing import Annotated

import duckdb  # noqa: TC002 — runtime-required for FastAPI annotation resolution
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.models.clusters import ClusterCommentOut, ClusterSummary
from db.queries import get_cluster_comments, get_clusters_by_docket

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("/{docket_id}", response_model=list[ClusterSummary])
def list_clusters(
    docket_id: str,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> list[ClusterSummary]:
    """Return cluster summaries for a docket."""
    rows = get_clusters_by_docket(db, docket_id)
    return [ClusterSummary.model_validate(r) for r in rows]


@router.get("/{docket_id}/{cluster_id}", response_model=list[ClusterCommentOut])
def list_cluster_comments(
    docket_id: str,
    cluster_id: int,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> list[ClusterCommentOut]:
    """Return comments belonging to a specific cluster."""
    rows = get_cluster_comments(db, docket_id, cluster_id, limit=limit)
    return [ClusterCommentOut.model_validate(r) for r in rows]
