"""Pydantic schemas for astroturf detection API responses."""

from __future__ import annotations

from pydantic import BaseModel


class DuplicateGroupOut(BaseModel):
    """A group of duplicate/near-duplicate comments."""

    group_id: int
    comment_ids: list[str]
    group_size: int
    unique_submitters: int
    campaign_likelihood: float
    is_astroturf: bool
    template_text: str | None = None


class DuplicateGroupListResponse(BaseModel):
    """Paginated list of duplicate groups."""

    items: list[DuplicateGroupOut]
    total: int
    limit: int
    offset: int


class GroupCommentOut(BaseModel):
    """A single comment that belongs to a duplicate/astroturf group."""

    comment_id: str
    comment_text: str | None = None
    submitter_name: str | None = None


class AstroturfSummaryResponse(BaseModel):
    """Summary statistics for astroturf detection."""

    total_groups: int
    astroturf_groups: int
    total_flagged_comments: int
    max_campaign_likelihood: float
