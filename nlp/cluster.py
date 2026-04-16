"""HDBSCAN clustering of comment embeddings, scoped per-docket."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import polars as pl
    from numpy.typing import NDArray

logger = logging.getLogger(__name__)

DEFAULT_MIN_CLUSTER_SIZE = 15


@dataclass(frozen=True, slots=True)
class ClusterResult:
    """Clustering output for a single docket."""

    docket_id: str
    comment_ids: tuple[str, ...]
    labels: tuple[int, ...]
    n_clusters: int
    n_noise: int


def cluster_embeddings(
    comment_ids: list[str],
    embeddings: NDArray[np.float32],
    *,
    docket_id: str,
    min_cluster_size: int = DEFAULT_MIN_CLUSTER_SIZE,
) -> ClusterResult:
    """Run HDBSCAN on pre-computed embeddings for a single docket.

    Noise points receive ``cluster_id = -1``.
    """
    import hdbscan

    if len(comment_ids) == 0 or embeddings.shape[0] == 0:
        return ClusterResult(
            docket_id=docket_id,
            comment_ids=(),
            labels=(),
            n_clusters=0,
            n_noise=0,
        )

    effective_min = min(min_cluster_size, len(comment_ids))
    if effective_min < 2:
        effective_min = 2

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=effective_min,
        metric="euclidean",
        cluster_selection_method="eom",
    )
    labels_array: NDArray[np.int64] = clusterer.fit_predict(embeddings)
    labels = tuple(int(lbl) for lbl in labels_array)

    n_clusters = len(set(labels) - {-1})
    n_noise = labels.count(-1)

    logger.info(
        "docket %s: %d clusters, %d noise points from %d comments",
        docket_id,
        n_clusters,
        n_noise,
        len(comment_ids),
    )

    return ClusterResult(
        docket_id=docket_id,
        comment_ids=tuple(comment_ids),
        labels=labels,
        n_clusters=n_clusters,
        n_noise=n_noise,
    )


def cluster_result_to_dataframe(result: ClusterResult) -> pl.DataFrame:
    """Convert a ClusterResult to a Polars DataFrame for storage."""
    import polars as pl

    if not result.comment_ids:
        return pl.DataFrame(
            schema={
                "comment_id": pl.String,
                "docket_id": pl.String,
                "cluster_id": pl.Int64,
            }
        )

    return pl.DataFrame(
        {
            "comment_id": list(result.comment_ids),
            "docket_id": [result.docket_id] * len(result.comment_ids),
            "cluster_id": list(result.labels),
        }
    )
