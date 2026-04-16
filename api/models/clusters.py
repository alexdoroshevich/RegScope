"""Pydantic schemas for cluster-related API responses."""

from __future__ import annotations

from pydantic import BaseModel


class ClusterSummary(BaseModel):
    """Cluster with its comment count."""

    cluster_id: int
    comment_count: int


class ClusterCommentOut(BaseModel):
    """Comment belonging to a cluster."""

    comment_id: str
    comment_text: str | None = None
    submitter_name: str | None = None
