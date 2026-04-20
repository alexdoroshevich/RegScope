"""Pydantic schemas for the NL query (RAG) endpoint."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request body for POST /api/v1/query."""

    docket_id: str = Field(..., description="Regulations.gov docket ID to search within.")
    question: str = Field(
        ..., min_length=1, max_length=1000, description="Natural-language question."
    )
    top_k: int = Field(
        default=10, ge=1, le=50, description="Number of source comments to retrieve."
    )


class SourceCommentResponse(BaseModel):
    """A single retrieved comment used as RAG context."""

    comment_id: str
    docket_id: str
    comment_text: str
    similarity: float


class QueryResponse(BaseModel):
    """Response from POST /api/v1/query."""

    question: str
    answer: str
    sources: list[SourceCommentResponse]
    model: str
    cost_usd: float
    from_cache: bool
