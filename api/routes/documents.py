"""Federal Register documents endpoint."""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, Query

from api.deps import get_db
from api.models.documents import DocumentListResponse, DocumentOut
from db.queries import count_documents, list_documents

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
def list_docs(
    docket_id: Annotated[str | None, Query(max_length=200)] = None,
    doc_type: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    *,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
) -> DocumentListResponse:
    """Return Federal Register documents, optionally filtered by docket or document type.

    Results are ordered by ``publication_date`` descending (newest first).
    Documents with no publication date sort last.
    """
    rows = list_documents(db, docket_id=docket_id, doc_type=doc_type, limit=limit, offset=offset)
    total = count_documents(db, docket_id=docket_id, doc_type=doc_type)
    return DocumentListResponse(
        items=[DocumentOut.model_validate(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
