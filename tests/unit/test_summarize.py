"""Tests for nlp/summarize.py — LLM cluster labeling with caching."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from nlp.summarize import (
    ClusterLabel,
    _build_user_prompt,
    _hash_prompt,
    _load_cache,
    _parse_response,
    _save_cache,
    label_cluster,
    label_clusters_for_docket,
)

if TYPE_CHECKING:
    from pathlib import Path


class TestHashPrompt:
    def test_deterministic(self) -> None:
        h1 = _hash_prompt("hello", "gpt-4o-mini")
        h2 = _hash_prompt("hello", "gpt-4o-mini")
        assert h1 == h2

    def test_different_model_different_hash(self) -> None:
        h1 = _hash_prompt("hello", "gpt-4o-mini")
        h2 = _hash_prompt("hello", "gpt-4o")
        assert h1 != h2

    def test_different_prompt_different_hash(self) -> None:
        h1 = _hash_prompt("hello", "gpt-4o-mini")
        h2 = _hash_prompt("world", "gpt-4o-mini")
        assert h1 != h2


class TestBuildUserPrompt:
    def test_includes_comments(self) -> None:
        prompt = _build_user_prompt(["Comment A", "Comment B"])
        assert "Comment A" in prompt
        assert "Comment B" in prompt

    def test_limits_to_five(self) -> None:
        comments = [f"Comment {i}" for i in range(10)]
        prompt = _build_user_prompt(comments)
        assert "Comment 4" in prompt
        assert "Comment 5" not in prompt

    def test_truncates_long_comments(self) -> None:
        long_comment = "x" * 1000
        prompt = _build_user_prompt([long_comment])
        assert len(long_comment) > 500
        assert "x" * 500 in prompt
        assert "x" * 501 not in prompt


class TestParseResponse:
    def test_numbered_format(self) -> None:
        text = "1. Environmental Regulation\n2. Comments focus on air quality standards."
        label, summary = _parse_response(text)
        assert label == "Environmental Regulation"
        assert "air quality" in summary

    def test_labeled_format(self) -> None:
        text = "Label: Water Safety\nSummary: Concerns about drinking water."
        label, summary = _parse_response(text)
        assert label == "Water Safety"
        assert "drinking water" in summary

    def test_unclear_default(self) -> None:
        text = ""
        label, _summary = _parse_response(text)
        assert label == "Unclear"

    def test_strips_markdown_bold(self) -> None:
        text = "1. **Clean Energy**\n2. **Comments support renewable energy incentives.**"
        label, _summary = _parse_response(text)
        assert label == "Clean Energy"

    def test_topic_theme_format(self) -> None:
        text = "Topic: Worker Safety\nTheme: Comments call for stricter OSHA rules."
        label, summary = _parse_response(text)
        assert label == "Worker Safety"
        assert "OSHA" in summary


class TestCache:
    def test_load_empty_cache(self, tmp_path: Path) -> None:
        cache = _load_cache(tmp_path / "nonexistent.parquet")
        assert cache == {}

    def test_save_and_load(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.parquet"
        entries = [
            ClusterLabel(
                docket_id="DOC-1",
                cluster_id=0,
                label="Test Label",
                summary="Test summary",
                prompt_hash="abc123",
                model="gpt-4o-mini",
                cost_usd=0.001,
            ),
        ]
        _save_cache(cache_path, entries)
        loaded = _load_cache(cache_path)
        assert "abc123" in loaded
        assert loaded["abc123"] == ("Test Label", "Test summary")

    def test_append_to_existing(self, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.parquet"
        entry1 = ClusterLabel(
            docket_id="DOC-1",
            cluster_id=0,
            label="L1",
            summary="S1",
            prompt_hash="h1",
            model="gpt-4o-mini",
            cost_usd=0.001,
        )
        entry2 = ClusterLabel(
            docket_id="DOC-1",
            cluster_id=1,
            label="L2",
            summary="S2",
            prompt_hash="h2",
            model="gpt-4o-mini",
            cost_usd=0.002,
        )
        _save_cache(cache_path, [entry1])
        _save_cache(cache_path, [entry2])
        loaded = _load_cache(cache_path)
        assert len(loaded) == 2


def _mock_litellm_response(
    content: str, prompt_tokens: int = 100, completion_tokens: int = 50
) -> MagicMock:
    """Build a mock litellm completion response."""
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    message = MagicMock()
    message.content = content

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    response.usage = usage
    return response


class TestLabelCluster:
    def test_cache_hit(self) -> None:
        cache = {"somehash": ("Cached Label", "Cached summary")}
        result = label_cluster(
            ["comment"],
            docket_id="DOC-1",
            cluster_id=0,
            cache=cache,
        )
        assert result.cost_usd == 0.0

    @patch("litellm.completion")
    def test_llm_call(self, mock_completion: MagicMock) -> None:
        mock_completion.return_value = _mock_litellm_response(
            "1. Air Quality\n2. Comments discuss pollution standards."
        )
        result = label_cluster(
            ["Pollution is bad", "We need cleaner air"],
            docket_id="DOC-1",
            cluster_id=0,
        )
        assert result.label == "Air Quality"
        assert "pollution" in result.summary.lower()
        assert result.cost_usd > 0
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_llm_failure_returns_unclear(self, mock_completion: MagicMock) -> None:
        mock_completion.side_effect = RuntimeError("API down")
        result = label_cluster(
            ["comment"],
            docket_id="DOC-1",
            cluster_id=0,
        )
        assert result.label == "Unclear"
        assert result.cost_usd == 0.0


class TestLabelClustersForDocket:
    @patch("litellm.completion")
    def test_labels_multiple_clusters(self, mock_completion: MagicMock, tmp_path: Path) -> None:
        mock_completion.return_value = _mock_litellm_response(
            "1. Test Topic\n2. Test summary here."
        )
        cluster_comments: dict[int, list[str]] = {
            0: ["Comment A", "Comment B"],
            1: ["Comment C", "Comment D"],
        }
        results = label_clusters_for_docket(
            cluster_comments,
            docket_id="DOC-1",
            cache_path=tmp_path / "cache.parquet",
            rate_limit_delay=0.0,
        )
        assert len(results) == 2
        assert mock_completion.call_count == 2

    @patch("litellm.completion")
    def test_skips_noise_cluster(self, mock_completion: MagicMock, tmp_path: Path) -> None:
        mock_completion.return_value = _mock_litellm_response("1. Topic\n2. Summary.")
        cluster_comments: dict[int, list[str]] = {
            -1: ["Noise comment"],
            0: ["Real comment"],
        }
        results = label_clusters_for_docket(
            cluster_comments,
            docket_id="DOC-1",
            cache_path=tmp_path / "cache.parquet",
            rate_limit_delay=0.0,
        )
        assert len(results) == 1
        assert results[0].cluster_id == 0

    @patch("litellm.completion")
    def test_uses_cache(self, mock_completion: MagicMock, tmp_path: Path) -> None:
        cache_path = tmp_path / "cache.parquet"
        mock_completion.return_value = _mock_litellm_response("1. First Topic\n2. First summary.")
        label_clusters_for_docket(
            {0: ["Comment A"]},
            docket_id="DOC-1",
            cache_path=cache_path,
            rate_limit_delay=0.0,
        )
        assert mock_completion.call_count == 1

        label_clusters_for_docket(
            {0: ["Comment A"]},
            docket_id="DOC-1",
            cache_path=cache_path,
            rate_limit_delay=0.0,
        )
        assert mock_completion.call_count == 1
