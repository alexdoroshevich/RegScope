"""Pydantic schemas for comment-related API responses."""

from __future__ import annotations

from pydantic import BaseModel


class CommentOut(BaseModel):
    """Single comment returned by the API."""

    comment_id: str
    docket_id: str
    posted_date: str | None = None
    submitter_name: str | None = None
    comment_text: str | None = None


class CommentListResponse(BaseModel):
    """Paginated list of comments."""

    items: list[CommentOut]
    total: int
    limit: int
    offset: int
