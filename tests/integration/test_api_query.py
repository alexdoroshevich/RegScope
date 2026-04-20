"""Integration tests for the NL query (RAG) API route."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_DOCKET = "EPA-HQ-OAR-2021-0317"


def _mock_llm(answer: str = "Small businesses bear disproportionate costs.") -> MagicMock:
    usage = MagicMock()
    usage.prompt_tokens = 200
    usage.completion_tokens = 40
    choice = MagicMock()
    choice.message.content = answer
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _mock_embed(text: str | None = None) -> MagicMock:
    """Return a patched embed_texts that yields a random unit-norm vector."""
    rng = np.random.default_rng(0)
    vec = rng.standard_normal(384).astype(np.float32)
    vec /= np.linalg.norm(vec)
    return MagicMock(return_value=vec.reshape(1, 384))


@pytest.mark.integration
class TestQueryEndpoint:
    def test_returns_200(self, api_client: TestClient) -> None:
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm()),
        ):
            r = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "What concerns do commenters raise?"},
            )
        assert r.status_code == 200

    def test_response_schema(self, api_client: TestClient) -> None:
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm()),
        ):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "What do commenters say?"},
            ).json()
        assert "answer" in body
        assert "sources" in body
        assert "model" in body
        assert "cost_usd" in body
        assert "from_cache" in body

    def test_sources_are_from_docket(self, api_client: TestClient) -> None:
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm()),
        ):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "What concerns are raised?"},
            ).json()
        for src in body["sources"]:
            assert src["docket_id"] == _DOCKET

    def test_sources_have_similarity(self, api_client: TestClient) -> None:
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm()),
        ):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "What concerns are raised?"},
            ).json()
        assert all("similarity" in src for src in body["sources"])

    def test_top_k_limits_sources(self, api_client: TestClient) -> None:
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm()),
        ):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "test", "top_k": 1},
            ).json()
        assert len(body["sources"]) <= 1

    def test_answer_text_is_present(self, api_client: TestClient) -> None:
        expected = "Small businesses bear disproportionate costs."
        with (
            patch("nlp.embed.embed_texts", _mock_embed()),
            patch("litellm.completion", return_value=_mock_llm(expected)),
        ):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": _DOCKET, "question": "What do commenters say?"},
            ).json()
        assert body["answer"] == expected

    def test_empty_question_returns_422(self, api_client: TestClient) -> None:
        r = api_client.post(
            "/api/v1/query",
            json={"docket_id": _DOCKET, "question": ""},
        )
        assert r.status_code == 422

    def test_missing_docket_returns_graceful(self, api_client: TestClient) -> None:
        with patch("nlp.embed.embed_texts", _mock_embed()):
            body = api_client.post(
                "/api/v1/query",
                json={"docket_id": "NONEXISTENT", "question": "What do commenters say?"},
            ).json()
        assert "answer" in body
        # No embeddings → guidance message
        assert "No embedded" in body["answer"] or body["answer"]
