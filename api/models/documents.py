"""Pydantic schemas for Federal Register documents API responses."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime access

from pydantic import BaseModel


class DocumentOut(BaseModel):
    """A single Federal Register document."""

    document_number: str
    docket_id: str | None
    title: str
    doc_type: str
    abstract: str | None
    agency_names: str | None  # JSON-encoded list, e.g. '["EPA"]'
    publication_date: str | None  # YYYY-MM-DD string
    effective_on: str | None
    comments_close_on: str | None
    html_url: str | None
    citation: str | None
    significant: bool | None
    fetched_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of Federal Register documents."""

    items: list[DocumentOut]
    total: int
    limit: int
    offset: int
