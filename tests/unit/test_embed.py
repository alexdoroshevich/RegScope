"""Tests for nlp.embed — sentence-transformer embedding pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import polars as pl
import pytest

from nlp.embed import (
    EMBEDDING_DIM,
    embed_comments,
    embed_texts,
    reset_model,
)


@pytest.fixture(autouse=True)
def _clear_model_cache() -> None:
    reset_model()


@pytest.fixture()
def mock_model() -> MagicMock:
    """A mock SentenceTransformer that returns deterministic embeddings."""
    model = MagicMock()

    def _encode(
        texts: list[str],
        batch_size: int = 256,
        show_progress_bar: bool = False,
        convert_to_numpy: bool = True,
        normalize_embeddings: bool = True,
    ) -> np.ndarray:
        n = len(texts)
        rng = np.random.default_rng(42)
        vecs = rng.standard_normal((n, EMBEDDING_DIM)).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        return vecs / norms

    model.encode = MagicMock(side_effect=_encode)
    return model


class TestEmbedTexts:
    def test_output_shape_and_dtype(self, mock_model: MagicMock) -> None:
        texts = ["hello world", "foo bar baz"]
        result = embed_texts(texts, model=mock_model)
        assert result.shape == (2, EMBEDDING_DIM)
        assert result.dtype == np.float32

    def test_empty_input(self, mock_model: MagicMock) -> None:
        result = embed_texts([], model=mock_model)
        assert result.shape == (0, EMBEDDING_DIM)
        assert result.dtype == np.float32
        mock_model.encode.assert_not_called()

    def test_batch_size_forwarded(self, mock_model: MagicMock) -> None:
        embed_texts(["a", "b", "c"], model=mock_model, batch_size=64)
        mock_model.encode.assert_called_once()
        _, kwargs = mock_model.encode.call_args
        assert kwargs["batch_size"] == 64

    def test_normalize_embeddings_enabled(self, mock_model: MagicMock) -> None:
        embed_texts(["text"], model=mock_model)
        _, kwargs = mock_model.encode.call_args
        assert kwargs["normalize_embeddings"] is True


class TestEmbedComments:
    def test_returns_correct_schema(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a", "b"],
                "comment_text": ["hello world", "foo bar"],
            }
        )
        result = embed_comments(df, model=mock_model)
        assert result.columns == ["comment_id", "embedding"]
        assert result.schema["comment_id"] == pl.String
        assert result.schema["embedding"] == pl.List(pl.Float32)
        assert result.shape[0] == 2

    def test_skips_already_embedded(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a", "b", "c"],
                "comment_text": ["text a", "text b", "text c"],
            }
        )
        result = embed_comments(df, already_embedded=frozenset({"a", "c"}), model=mock_model)
        assert result.shape[0] == 1
        assert result["comment_id"].to_list() == ["b"]

    def test_skips_null_text(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a", "b"],
                "comment_text": [None, "valid text"],
            }
        )
        result = embed_comments(df, model=mock_model)
        assert result.shape[0] == 1
        assert result["comment_id"].to_list() == ["b"]

    def test_skips_empty_text(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a", "b"],
                "comment_text": ["", "valid text"],
            }
        )
        result = embed_comments(df, model=mock_model)
        assert result.shape[0] == 1

    def test_all_skipped_returns_empty(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a"],
                "comment_text": ["text"],
            }
        )
        result = embed_comments(df, already_embedded=frozenset({"a"}), model=mock_model)
        assert result.is_empty()
        assert result.columns == ["comment_id", "embedding"]

    def test_embedding_dimension(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a"],
                "comment_text": ["some regulatory comment text"],
            }
        )
        result = embed_comments(df, model=mock_model)
        embedding = result["embedding"][0].to_list()
        assert len(embedding) == EMBEDDING_DIM

    def test_embedding_values_are_float32(self, mock_model: MagicMock) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a"],
                "comment_text": ["some text"],
            }
        )
        result = embed_comments(df, model=mock_model)
        embedding = result["embedding"][0].to_list()
        assert all(isinstance(v, float) for v in embedding)
