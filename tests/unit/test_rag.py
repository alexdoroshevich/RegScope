"""Unit tests for nlp/rag.py."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from nlp.rag import (
    RagAnswer,
    SourceComment,
    _build_context,
    _estimate_cost,
    _hash_prompt,
    _load_cache,
    _save_to_cache,
    answer_question,
    retrieve_similar_comments,
)

# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


class TestHashPrompt:
    def test_returns_64_char_hex(self) -> None:
        h = _hash_prompt("hello", "gpt-4o-mini")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_prompts_differ(self) -> None:
        assert _hash_prompt("a", "m") != _hash_prompt("b", "m")

    def test_different_models_differ(self) -> None:
        assert _hash_prompt("a", "m1") != _hash_prompt("a", "m2")

    def test_deterministic(self) -> None:
        assert _hash_prompt("x", "y") == _hash_prompt("x", "y")


class TestEstimateCost:
    def test_gpt4o_mini(self) -> None:
        cost = _estimate_cost(1_000_000, 1_000_000, "gpt-4o-mini")
        assert abs(cost - 0.75) < 0.01

    def test_zero_tokens(self) -> None:
        assert _estimate_cost(0, 0, "gpt-4o-mini") == 0.0

    def test_unknown_model_uses_defaults(self) -> None:
        cost = _estimate_cost(100, 100, "unknown-model")
        assert cost > 0


class TestBuildContext:
    def test_basic(self) -> None:
        sources = [
            SourceComment("C-1", "D", "First comment", 0.9),
            SourceComment("C-2", "D", "Second comment", 0.8),
        ]
        ctx = _build_context(sources)
        assert "[1]" in ctx
        assert "id=C-1" in ctx
        assert "[2]" in ctx
        assert "Second comment" in ctx

    def test_truncates_long_text(self) -> None:
        src = SourceComment("C-1", "D", "x" * 1000, 0.9)
        ctx = _build_context([src], max_chars_per_comment=100)
        assert len(ctx) < 300

    def test_empty_sources(self) -> None:
        assert _build_context([]) == ""


# ---------------------------------------------------------------------------
# Cache round-trip
# ---------------------------------------------------------------------------


class TestCache:
    def test_save_and_load(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "rag_cache.parquet"
        _save_to_cache(cache_file, "abc123", "The answer", "gpt-4o-mini", 0.001)
        loaded = _load_cache(cache_file)
        assert loaded["abc123"] == "The answer"

    def test_load_missing_file_returns_empty(self, tmp_path: Path) -> None:
        assert _load_cache(tmp_path / "nonexistent.parquet") == {}

    def test_append_does_not_overwrite(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "rag_cache.parquet"
        _save_to_cache(cache_file, "key1", "answer1", "gpt-4o-mini", 0.0)
        _save_to_cache(cache_file, "key2", "answer2", "gpt-4o-mini", 0.0)
        loaded = _load_cache(cache_file)
        assert loaded["key1"] == "answer1"
        assert loaded["key2"] == "answer2"


# ---------------------------------------------------------------------------
# retrieve_similar_comments
# ---------------------------------------------------------------------------


class TestRetrieveSimilarComments:
    def _make_conn(self, rows: list[tuple[str, str, str, float]]) -> MagicMock:
        conn = MagicMock()
        conn.execute.return_value.fetchall.return_value = rows
        return conn

    def test_returns_source_comments(self) -> None:
        conn = self._make_conn([("C-1", "D", "text", 0.95)])
        vec = np.zeros(384, dtype=np.float32)
        results = retrieve_similar_comments(conn, vec, "D")
        assert len(results) == 1
        assert results[0].comment_id == "C-1"
        assert results[0].similarity == pytest.approx(0.95)

    def test_empty_result(self) -> None:
        conn = self._make_conn([])
        vec = np.zeros(384, dtype=np.float32)
        results = retrieve_similar_comments(conn, vec, "D")
        assert results == []

    def test_passes_docket_id_to_query(self) -> None:
        conn = self._make_conn([])
        vec = np.zeros(384, dtype=np.float32)
        retrieve_similar_comments(conn, vec, "MY-DOCKET", top_k=5)
        call_args = conn.execute.call_args
        assert "MY-DOCKET" in call_args[0][1]
        assert 5 in call_args[0][1]


# ---------------------------------------------------------------------------
# answer_question — with mocked LLM and embeddings
# ---------------------------------------------------------------------------


_FAKE_SOURCES = [
    SourceComment("C-001", "D-1", "Small businesses will be harmed.", 0.92),
    SourceComment("C-002", "D-1", "Compliance costs are too high.", 0.88),
]


def _make_litellm_response(content: str) -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = 100
    usage.completion_tokens = 50
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


class TestAnswerQuestion:
    def _mock_retrieval(self, sources: list[SourceComment]) -> MagicMock:
        """Patch retrieve_similar_comments to return fixed sources."""
        m = MagicMock(return_value=sources)
        return m

    def test_empty_question_returns_immediately(self) -> None:
        conn = MagicMock()
        result = answer_question(conn, "   ", "D-1")
        assert "non-empty" in result.answer.lower()
        conn.execute.assert_not_called()

    def test_no_embeddings_returns_guidance(self) -> None:
        conn = MagicMock()
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=[]),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
        ):
            result = answer_question(conn, "What do commenters say?", "D-1")
        assert "No embedded comments" in result.answer

    def test_llm_called_with_context(self, tmp_path: Path) -> None:
        conn = MagicMock()
        llm_resp = _make_litellm_response("Small businesses are mentioned in 3 comments.")
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=_FAKE_SOURCES),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
            patch("litellm.completion", return_value=llm_resp),
        ):
            result = answer_question(
                conn,
                "What do commenters say?",
                "D-1",
                cache_path=tmp_path / "cache.parquet",
            )
        assert result.answer == "Small businesses are mentioned in 3 comments."
        assert len(result.sources) == 2
        assert result.from_cache is False

    def test_cache_hit_skips_llm(self, tmp_path: Path) -> None:
        cache_file = tmp_path / "cache.parquet"
        conn = MagicMock()
        llm_resp = _make_litellm_response("Fresh answer")

        # First call — populates cache
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=_FAKE_SOURCES),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
            patch("litellm.completion", return_value=llm_resp) as mock_llm,
        ):
            answer_question(conn, "What do commenters say?", "D-1", cache_path=cache_file)
            assert mock_llm.call_count == 1

        # Second call — should be a cache hit
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=_FAKE_SOURCES),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
            patch("litellm.completion") as mock_llm2,
        ):
            result = answer_question(conn, "What do commenters say?", "D-1", cache_path=cache_file)
            mock_llm2.assert_not_called()
        assert result.from_cache is True

    def test_llm_failure_returns_graceful_error(self) -> None:
        conn = MagicMock()
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=_FAKE_SOURCES),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
            patch("litellm.completion", side_effect=RuntimeError("timeout")),
        ):
            result = answer_question(conn, "What do commenters say?", "D-1")
        assert "failed" in result.answer.lower()
        assert isinstance(result, RagAnswer)

    def test_cost_recorded(self, tmp_path: Path) -> None:
        conn = MagicMock()
        llm_resp = _make_litellm_response("answer")
        with (
            patch("nlp.rag.retrieve_similar_comments", return_value=_FAKE_SOURCES),
            patch("nlp.embed.embed_texts", return_value=np.zeros((1, 384), dtype=np.float32)),
            patch("litellm.completion", return_value=llm_resp),
        ):
            result = answer_question(
                conn,
                "What do commenters say?",
                "D-1",
                cache_path=tmp_path / "cache.parquet",
            )
        assert result.cost_usd > 0
