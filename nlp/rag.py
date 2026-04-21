"""RAG (Retrieval-Augmented Generation) for natural-language queries over comments.

Flow:
  1. Embed the user question with all-MiniLM-L6-v2 (same model used for comments).
  2. Retrieve top-k most-similar comments from DuckDB via cosine similarity.
  3. Build a context prompt from retrieved snippets.
  4. Call GPT-4o-mini via litellm; cache the response keyed on (prompt_hash, model).
  5. Return the answer together with the source comment IDs.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    import duckdb
    import numpy as np
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TOP_K = 10
DEFAULT_MAX_TOKENS = 600
DEFAULT_TEMPERATURE = 0.2

_SYSTEM_PROMPT = (
    "You are an analyst of public regulatory comments. "
    "Answer the user's question using ONLY the comment excerpts provided below. "
    "Cite specific comments by their ID (e.g. 'Comment C-001 argues…'). "
    "If the answer cannot be determined from the excerpts, say so explicitly. "
    "Be concise: 3-5 sentences maximum."
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SourceComment:
    """A comment retrieved as relevant context."""

    comment_id: str
    docket_id: str
    comment_text: str
    similarity: float


@dataclass(frozen=True, slots=True)
class RagAnswer:
    """Result of a RAG query."""

    question: str
    answer: str
    sources: list[SourceComment] = field(default_factory=list)
    prompt_hash: str = ""
    model: str = DEFAULT_MODEL
    cost_usd: float = 0.0
    from_cache: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sanitize_for_log(value: str, max_len: int = 80) -> str:
    """Strip newline/CR characters to prevent log-injection attacks."""
    return value[:max_len].replace("\n", "\\n").replace("\r", "\\r")


def _hash_prompt(prompt: str, model: str) -> str:
    """SHA-256 hash of the full prompt + model name for cache keying."""
    return hashlib.sha256(f"{prompt}|{model}".encode()).hexdigest()


def _build_context(sources: list[SourceComment], max_chars_per_comment: int = 400) -> str:
    """Format retrieved comments into a numbered context block."""
    lines: list[str] = []
    for i, src in enumerate(sources, 1):
        snippet = src.comment_text[:max_chars_per_comment].replace("\n", " ")
        lines.append(f"[{i}] (id={src.comment_id}) {snippet}")
    return "\n\n".join(lines)


def _estimate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """Estimate USD cost for a litellm call."""
    rates: dict[str, tuple[float, float]] = {
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
    }
    in_rate, out_rate = rates.get(model, (0.15 / 1_000_000, 0.60 / 1_000_000))
    return prompt_tokens * in_rate + completion_tokens * out_rate


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


def _load_cache(cache_path: Path) -> dict[str, str]:
    """Load RAG response cache from Parquet. Returns {prompt_hash: answer}."""
    if not cache_path.exists():
        return {}
    import polars as pl

    df = pl.read_parquet(cache_path)
    return dict(zip(df["prompt_hash"].to_list(), df["answer"].to_list(), strict=True))


def _save_to_cache(
    cache_path: Path, prompt_hash: str, answer: str, model: str, cost_usd: float
) -> None:
    """Append a new entry to the Parquet cache."""
    import polars as pl

    new_row = pl.DataFrame(
        {
            "prompt_hash": [prompt_hash],
            "model": [model],
            "answer": [answer],
            "cost_usd": [cost_usd],
        },
    )
    if cache_path.exists():
        existing = pl.read_parquet(cache_path)
        combined = pl.concat([existing, new_row])
    else:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        combined = new_row
    combined.write_parquet(cache_path)
    logger.debug("rag cache: saved entry %s to %s", prompt_hash[:8], cache_path)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def retrieve_similar_comments(
    conn: duckdb.DuckDBPyConnection,
    query_embedding: NDArray[np.float32],
    docket_id: str,
    *,
    top_k: int = DEFAULT_TOP_K,
) -> list[SourceComment]:
    """Return the top-k comments most similar to *query_embedding*.

    Cosine similarity is computed via dot product; embeddings stored in DuckDB
    are already L2-normalised (produced by sentence-transformers with
    ``normalize_embeddings=True``).
    """

    # Flatten to a plain Python list for DuckDB parameter binding.
    vec: list[float] = query_embedding.flatten().tolist()

    rows = conn.execute(
        """
        SELECT
            comment_id,
            docket_id,
            comment_text,
            list_dot_product(embedding, ?::FLOAT[384]) AS similarity
        FROM comments
        WHERE docket_id = ?
          AND embedding IS NOT NULL
          AND comment_text IS NOT NULL
        ORDER BY similarity DESC
        LIMIT ?
        """,
        [vec, docket_id, top_k],
    ).fetchall()

    return [
        SourceComment(
            comment_id=str(row[0]),
            docket_id=str(row[1]),
            comment_text=str(row[2]),
            similarity=float(row[3]),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def answer_question(
    conn: duckdb.DuckDBPyConnection,
    question: str,
    docket_id: str,
    *,
    top_k: int = DEFAULT_TOP_K,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    cache_path: Path | None = None,
) -> RagAnswer:
    """Answer *question* using comments from *docket_id* as context.

    Args:
        conn: Live DuckDB connection (must have ``comments`` and ``embeddings`` tables).
        question: Natural-language question from the user.
        docket_id: Scope retrieval to this docket.
        top_k: Number of comments to retrieve as context.
        model: litellm model string.
        temperature: LLM sampling temperature.
        max_tokens: Max completion tokens.
        cache_path: Optional Parquet file for caching responses.
    """
    import litellm

    from nlp.embed import embed_texts

    if not question.strip():
        return RagAnswer(question=question, answer="Please provide a non-empty question.")

    # 1. Embed the question.
    query_vec = embed_texts([question.strip()])  # shape (1, 384)

    # 2. Retrieve top-k similar comments.
    sources = retrieve_similar_comments(conn, query_vec[0], docket_id, top_k=top_k)

    if not sources:
        return RagAnswer(
            question=question,
            answer=(
                f"No embedded comments found for docket '{docket_id}'. "
                "Run the pipeline (embed step) first."
            ),
            sources=[],
        )

    # 3. Build the prompt.
    context = _build_context(sources)
    user_prompt = (
        f"Docket: {docket_id}\n\nComment excerpts:\n{context}\n\nQuestion: {question.strip()}"
    )
    prompt_hash = _hash_prompt(user_prompt, model)

    # 4. Check cache.
    cache: dict[str, str] = _load_cache(cache_path) if cache_path else {}
    if prompt_hash in cache:
        logger.info("rag cache hit for question %r", _sanitize_for_log(question))
        return RagAnswer(
            question=question,
            answer=cache[prompt_hash],
            sources=sources,
            prompt_hash=prompt_hash,
            model=model,
            cost_usd=0.0,
            from_cache=True,
        )

    # 5. Call the LLM.
    try:
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as err:
        # Classify the most common surface errors so the UI can show an
        # actionable message instead of a generic "try again".
        from litellm.exceptions import (
            APIConnectionError,
            AuthenticationError,
            RateLimitError,
        )

        if isinstance(err, RateLimitError):
            msg = (
                "The OpenAI account associated with OPENAI_API_KEY has exhausted its "
                "quota. Top up billing at https://platform.openai.com/account/billing "
                "and retry. Retrieval still worked — see the source comments below."
            )
        elif isinstance(err, AuthenticationError):
            msg = (
                "OPENAI_API_KEY is missing or invalid. Check your .env file. "
                "Retrieval still worked — see the source comments below."
            )
        elif isinstance(err, APIConnectionError):
            msg = (
                "Could not reach the OpenAI API (network issue). Retrieval still "
                "worked — see the source comments below."
            )
        else:
            msg = f"LLM call failed: {type(err).__name__}. Retrieval still worked — see the source comments below."

        logger.exception("RAG LLM call failed for question %r", _sanitize_for_log(question))
        return RagAnswer(
            question=question,
            answer=msg,
            sources=sources,
            prompt_hash=prompt_hash,
            model=model,
        )

    answer_text = (response.choices[0].message.content or "").strip()
    usage = response.usage
    cost = _estimate_cost(
        usage.prompt_tokens if usage else 0,
        usage.completion_tokens if usage else 0,
        model,
    )

    logger.info(
        "rag answer generated: docket=%s question=%r cost=$%.6f",
        _sanitize_for_log(docket_id),
        _sanitize_for_log(question),
        cost,
    )

    # 6. Persist to cache.
    if cache_path:
        _save_to_cache(cache_path, prompt_hash, answer_text, model, cost)

    return RagAnswer(
        question=question,
        answer=answer_text,
        sources=sources,
        prompt_hash=prompt_hash,
        model=model,
        cost_usd=cost,
        from_cache=False,
    )
