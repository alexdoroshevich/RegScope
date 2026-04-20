"""Citation graph endpoint — cross-regulation reference network for a docket."""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.deps import get_db
from api.models.graph import GraphLink, GraphNode, GraphResponse
from db.queries import get_citation_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{docket_id}", response_model=GraphResponse)
def citation_graph(
    docket_id: str,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> GraphResponse:
    """Return graph nodes and links for a docket's citation network."""
    data = get_citation_graph(db, docket_id)
    return GraphResponse(
        nodes=[GraphNode.model_validate(n) for n in data["nodes"]],
        links=[GraphLink.model_validate(lnk) for lnk in data["links"]],
    )
