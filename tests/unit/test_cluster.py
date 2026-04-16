"""Tests for nlp.cluster — HDBSCAN clustering of comment embeddings."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from nlp.cluster import (
    ClusterResult,
    cluster_embeddings,
    cluster_result_to_dataframe,
)


def _make_blobs(
    n_per_cluster: int = 30,
    n_clusters: int = 3,
    dim: int = 10,
    spread: float = 0.1,
) -> tuple[list[str], np.ndarray]:
    """Generate synthetic clustered embeddings in low-dim space for testability."""
    rng = np.random.default_rng(42)
    ids: list[str] = []
    vectors: list[np.ndarray] = []
    for c in range(n_clusters):
        center = np.zeros(dim, dtype=np.float32)
        center[c % dim] = 5.0
        for i in range(n_per_cluster):
            vec = center + rng.standard_normal(dim).astype(np.float32) * spread
            vectors.append(vec)
            ids.append(f"cluster{c}-{i}")
    return ids, np.stack(vectors)


class TestClusterEmbeddings:
    def test_finds_known_clusters(self) -> None:
        ids, embeddings = _make_blobs(n_per_cluster=30, n_clusters=3)
        result = cluster_embeddings(ids, embeddings, docket_id="DOC-001")
        assert result.n_clusters >= 2
        assert result.docket_id == "DOC-001"
        assert len(result.comment_ids) == 90
        assert len(result.labels) == 90

    def test_noise_points_labeled_minus_one(self) -> None:
        ids, embeddings = _make_blobs(n_per_cluster=30, n_clusters=3)
        result = cluster_embeddings(ids, embeddings, docket_id="DOC-001")
        assert all(lbl >= -1 for lbl in result.labels)
        assert result.n_noise == result.labels.count(-1)

    def test_empty_input(self) -> None:
        result = cluster_embeddings(
            [],
            np.empty((0, 384), dtype=np.float32),
            docket_id="EMPTY",
        )
        assert result.n_clusters == 0
        assert result.n_noise == 0
        assert result.comment_ids == ()

    def test_small_input_does_not_crash(self) -> None:
        rng = np.random.default_rng(0)
        embeddings = rng.standard_normal((3, 384)).astype(np.float32)
        result = cluster_embeddings(
            ["a", "b", "c"],
            embeddings,
            docket_id="SMALL",
            min_cluster_size=15,
        )
        assert len(result.labels) == 3

    def test_custom_min_cluster_size(self) -> None:
        ids, embeddings = _make_blobs(n_per_cluster=10, n_clusters=2)
        result = cluster_embeddings(ids, embeddings, docket_id="DOC-002", min_cluster_size=5)
        assert result.n_clusters >= 1

    def test_dataclass_is_frozen(self) -> None:
        result = ClusterResult(
            docket_id="X",
            comment_ids=(),
            labels=(),
            n_clusters=0,
            n_noise=0,
        )
        with pytest.raises(AttributeError):
            result.n_clusters = 5  # type: ignore[misc]


class TestClusterResultToDataframe:
    def test_empty_result_schema(self) -> None:
        result = ClusterResult(
            docket_id="EMPTY",
            comment_ids=(),
            labels=(),
            n_clusters=0,
            n_noise=0,
        )
        df = cluster_result_to_dataframe(result)
        assert df.shape == (0, 3)
        assert df.columns == ["comment_id", "docket_id", "cluster_id"]

    def test_round_trip(self) -> None:
        ids, embeddings = _make_blobs(n_per_cluster=20, n_clusters=2)
        result = cluster_embeddings(ids, embeddings, docket_id="DOC-003")
        df = cluster_result_to_dataframe(result)
        assert df.shape[0] == 40
        assert df["docket_id"].unique().to_list() == ["DOC-003"]
        assert df.schema["cluster_id"] == pl.Int64
        assert set(df["cluster_id"].to_list()) >= {-1} or result.n_noise == 0
