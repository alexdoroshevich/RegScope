"""NL Query route — POST /api/v1/query."""

from __future__ import annotations

import logging
from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends

from api.config import Settings, get_settings
from api.deps import get_db
from api.models.query import QueryRequest, QueryResponse, SourceCommentResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query_comments(
    body: QueryRequest,
    db: Annotated[duckdb.DuckDBPyConnection, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> QueryResponse:
    """Answer a natural-language question over a docket's comments using RAG.

    Embeds the question, retrieves the most similar comments stored in DuckDB,
    and asks GPT-4o-mini to synthesise an answer from those excerpts.
    Responses are cached to a Parquet file so the same question never costs twice.
    """
    from nlp.rag import answer_question

    cache_path = settings.data_dir / "cache" / "rag_cache.parquet"

    result = answer_question(
        db,
        body.question,
        body.docket_id,
        top_k=body.top_k,
        cache_path=cache_path,
    )

    return QueryResponse(
        question=result.question,
        answer=result.answer,
        sources=[
            SourceCommentResponse(
                comment_id=src.comment_id,
                docket_id=src.docket_id,
                comment_text=src.comment_text,
                similarity=src.similarity,
            )
            for src in result.sources
        ],
        model=result.model,
        cost_usd=result.cost_usd,
        from_cache=result.from_cache,
    )
