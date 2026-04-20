"""Pydantic schemas for the citation graph API response."""

from __future__ import annotations

from pydantic import BaseModel


class GraphNode(BaseModel):
    """A node in the citation graph — either a docket or a regulation."""

    id: str
    label: str
    type: str  # 'docket' | 'regulation'
    count: int = 0
    citation_type: str | None = None


class GraphLink(BaseModel):
    """A directed edge from a docket node to a regulation node."""

    source: str
    target: str
    value: int


class GraphResponse(BaseModel):
    """Full graph payload for react-force-graph."""

    nodes: list[GraphNode]
    links: list[GraphLink]
