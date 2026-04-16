"""Sentence-transformer embedding pipeline for comment text."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np
    import polars as pl
    from numpy.typing import NDArray
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
DEFAULT_BATCH_SIZE = 256

_model: SentenceTransformer | None = None


def get_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    """Return a cached SentenceTransformer instance."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
        logger.info("loaded sentence-transformer model %s", model_name)
    return _model


def reset_model() -> None:
    """Clear the cached model (for testing)."""
    global _model
    _model = None


def embed_texts(
    texts: Sequence[str],
    *,
    model: SentenceTransformer | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> NDArray[np.float32]:
    """Encode a sequence of texts into float32 embeddings.

    Returns an (n, 384) numpy array.
    """
    import numpy as np

    if not texts:
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

    encoder = model or get_model()
    embeddings: NDArray[np.float32] = encoder.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return embeddings.astype(np.float32)


def embed_comments(
    comments: pl.DataFrame,
    *,
    already_embedded: frozenset[str] = frozenset(),
    model: SentenceTransformer | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> pl.DataFrame:
    """Generate embeddings for comments, skipping already-embedded IDs.

    Expects columns: ``comment_id``, ``comment_text``.
    Returns a DataFrame with ``comment_id`` and ``embedding`` (list[f32]).
    """
    import polars as pl

    to_embed = comments.filter(
        ~pl.col("comment_id").is_in(already_embedded)
        & pl.col("comment_text").is_not_null()
        & (pl.col("comment_text").str.len_chars() > 0)
    )

    if to_embed.is_empty():
        logger.info("no new comments to embed (all skipped or empty)")
        return pl.DataFrame(schema={"comment_id": pl.String, "embedding": pl.List(pl.Float32)})

    ids: list[str] = to_embed["comment_id"].to_list()
    texts: list[str] = to_embed["comment_text"].to_list()

    logger.info("embedding %d comments in batches of %d", len(texts), batch_size)
    vectors = embed_texts(texts, model=model, batch_size=batch_size)

    return pl.DataFrame(
        {
            "comment_id": ids,
            "embedding": vectors.tolist(),
        },
        schema={"comment_id": pl.String, "embedding": pl.List(pl.Float32)},
    )
