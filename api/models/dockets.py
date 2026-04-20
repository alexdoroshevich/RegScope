"""Pydantic schemas for docket-discovery API responses."""

from __future__ import annotations

from pydantic import BaseModel


class DocketOut(BaseModel):
    """Summary of a docket available in the database."""

    docket_id: str
    comment_count: int


class DocketListResponse(BaseModel):
    """Paginated list of dockets."""

    items: list[DocketOut]
    total: int
    limit: int
    offset: int
