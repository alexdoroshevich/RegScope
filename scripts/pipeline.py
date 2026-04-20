"""End-to-end pipeline CLI for a single docket.

Usage:
    uv run python -m scripts.pipeline EPA-HQ-OAR-2021-0317

Steps:
    1. Ingest  — fetch comments from Regulations.gov → Parquet
    2. Dedup   — MinHash/LSH near-duplicate detection → Parquet
    3. Embed   — sentence-transformers embeddings → Parquet
    4. Cluster — HDBSCAN per-docket clustering → Parquet
    5. Label   — GPT-4o-mini cluster labels (cached) → Parquet
    6. Load    — insert all Parquet artefacts into DuckDB
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from typing import TYPE_CHECKING

from api.config import get_settings

if TYPE_CHECKING:
    from pathlib import Path
from api.logging_setup import configure_logging

logger = logging.getLogger(__name__)


def _ingest(docket_id: str, data_dir: Path, api_key: str) -> Path:
    """Fetch comments from Regulations.gov and write to Parquet."""
    from data.ingest.regulations_gov import NormalizedComment, RegulationsGovClient
    from data.ingest.writer import write_comments_parquet

    async def _run() -> list[NormalizedComment]:
        async with RegulationsGovClient(api_key) as client:
            return [c async for c in client.iter_comments(docket_id)]

    comments = asyncio.run(_run())
    if not comments:
        logger.warning("no comments fetched for docket %s", docket_id)
        sys.exit(1)

    out = write_comments_parquet(comments, data_dir=data_dir, docket_id=docket_id)
    logger.info("ingested %d comments → %s", len(comments), out)
    return out


def _process(data_dir: Path, docket_id: str) -> Path:
    """Clean and validate raw comments, writing processed Parquet."""
    from data.process.clean import process_docket

    raw = data_dir / "comments" / f"docket_id={docket_id}" / "part-00000.parquet"
    out = data_dir / "processed" / docket_id / "comments.parquet"
    process_docket(raw, out)
    logger.info("process: cleaned comments → %s", out)
    return out


def _dedup(data_dir: Path, docket_id: str) -> Path:
    """Run MinHash/LSH dedup on processed comments."""
    import polars as pl

    from nlp.dedup import find_duplicate_groups, groups_to_dataframe

    pq = data_dir / "processed" / docket_id / "comments.parquet"
    comments = pl.read_parquet(pq)
    groups = find_duplicate_groups(comments)
    df = groups_to_dataframe(groups)

    out = data_dir / "processed" / docket_id / "duplicate_groups.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    logger.info("dedup: %d groups → %s", len(groups), out)
    return out


def _embed(data_dir: Path, docket_id: str) -> Path:
    """Generate sentence-transformer embeddings for comments."""
    import polars as pl

    from nlp.embed import embed_comments

    pq = data_dir / "processed" / docket_id / "comments.parquet"
    comments = pl.read_parquet(pq).select("comment_id", "comment_text")
    embeddings_df = embed_comments(comments)

    out = data_dir / "processed" / docket_id / "embeddings.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    embeddings_df.write_parquet(out)
    logger.info("embed: %d vectors → %s", embeddings_df.height, out)
    return out


def _cluster(data_dir: Path, docket_id: str, min_cluster_size: int) -> Path:
    """Run HDBSCAN clustering on embeddings."""
    import numpy as np
    import polars as pl

    from nlp.cluster import cluster_embeddings, cluster_result_to_dataframe

    emb_pq = data_dir / "processed" / docket_id / "embeddings.parquet"
    emb_df = pl.read_parquet(emb_pq)

    ids: list[str] = emb_df["comment_id"].to_list()
    vectors = np.array(emb_df["embedding"].to_list(), dtype=np.float32)

    result = cluster_embeddings(
        ids,
        vectors,
        docket_id=docket_id,
        min_cluster_size=min_cluster_size,
    )
    df = cluster_result_to_dataframe(result)

    out = data_dir / "processed" / docket_id / "clusters.parquet"
    df.write_parquet(out)
    logger.info("cluster: %d clusters, %d noise → %s", result.n_clusters, result.n_noise, out)
    return out


def _citations(data_dir: Path, docket_id: str) -> Path:
    """Extract CFR/USC citations from processed comments."""
    import polars as pl

    from nlp.citations import extract_citations_from_df

    pq = data_dir / "processed" / docket_id / "comments.parquet"
    comments = pl.read_parquet(pq).select("comment_id", "docket_id", "comment_text")
    citations_df = extract_citations_from_df(comments)

    out = data_dir / "processed" / docket_id / "citations.parquet"
    citations_df.write_parquet(out)
    logger.info("citations: %d extracted → %s", citations_df.height, out)
    return out


def _label(data_dir: Path, docket_id: str) -> Path:
    """Label clusters via GPT-4o-mini."""
    import polars as pl

    from nlp.summarize import label_clusters_for_docket

    cluster_pq = data_dir / "processed" / docket_id / "clusters.parquet"
    comment_pq = data_dir / "comments" / f"docket_id={docket_id}" / "part-00000.parquet"

    clusters_df = pl.read_parquet(cluster_pq)
    comments_df = pl.read_parquet(comment_pq).select("comment_id", "comment_text")

    merged = clusters_df.join(comments_df, on="comment_id", how="left")

    cluster_comments: dict[int, list[str]] = {}
    for row in merged.iter_rows(named=True):
        cid: int = row["cluster_id"]
        text: str = row["comment_text"] or ""
        if text:
            cluster_comments.setdefault(cid, []).append(text)

    cache_path = data_dir / "processed" / docket_id / "llm_cache.parquet"
    results = label_clusters_for_docket(
        cluster_comments,
        docket_id=docket_id,
        cache_path=cache_path,
    )

    labels_df = pl.DataFrame(
        {
            "docket_id": [r.docket_id for r in results],
            "cluster_id": [r.cluster_id for r in results],
            "label": [r.label for r in results],
            "summary": [r.summary for r in results],
            "prompt_hash": [r.prompt_hash for r in results],
            "model": [r.model for r in results],
            "cost_usd": [r.cost_usd for r in results],
        }
    )
    out = data_dir / "processed" / docket_id / "cluster_labels.parquet"
    labels_df.write_parquet(out)
    logger.info("label: %d clusters labeled → %s", len(results), out)
    return out


def _load_db(data_dir: Path, docket_id: str, db_path: Path) -> None:
    """Load all Parquet artefacts into DuckDB."""
    from db.init_db import (
        connect,
        load_citations,
        load_cluster_assignments,
        load_comments_parquet,
        load_duplicate_groups,
        load_embeddings,
    )
    from db.queries import upsert_cluster_label

    conn = connect(db_path)
    try:
        comment_pq = str(data_dir / "processed" / docket_id / "comments.parquet")
        load_comments_parquet(conn, comment_pq)

        groups_pq = data_dir / "processed" / docket_id / "duplicate_groups.parquet"
        if groups_pq.exists():
            load_duplicate_groups(conn, str(groups_pq))

        emb_pq = data_dir / "processed" / docket_id / "embeddings.parquet"
        if emb_pq.exists():
            load_embeddings(conn, str(emb_pq))

        clusters_pq = data_dir / "processed" / docket_id / "clusters.parquet"
        if clusters_pq.exists():
            load_cluster_assignments(conn, str(clusters_pq))

        labels_pq = data_dir / "processed" / docket_id / "cluster_labels.parquet"
        if labels_pq.exists():
            import polars as pl

            labels_df = pl.read_parquet(labels_pq)
            for row in labels_df.iter_rows(named=True):
                upsert_cluster_label(
                    conn,
                    docket_id=row["docket_id"],
                    cluster_id=row["cluster_id"],
                    label=row["label"],
                    summary=row["summary"],
                    prompt_hash=row["prompt_hash"],
                    model=row["model"],
                    cost_usd=row["cost_usd"],
                )
            logger.info("loaded %d cluster labels into DuckDB", labels_df.height)

        citations_pq = data_dir / "processed" / docket_id / "citations.parquet"
        if citations_pq.exists():
            load_citations(conn, str(citations_pq))
    finally:
        conn.close()

    logger.info("all artefacts loaded into %s", db_path)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Run the full RegScope pipeline for a single docket.",
    )
    parser.add_argument("docket_id", help="Regulations.gov docket ID")
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip fetching from Regulations.gov (use existing Parquet)",
    )
    parser.add_argument(
        "--skip-label",
        action="store_true",
        help="Skip LLM labeling (no OpenAI API cost)",
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=15,
        help="HDBSCAN min_cluster_size (default: 15)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the full pipeline."""
    args = _parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    docket_id: str = args.docket_id
    data_dir = settings.data_dir
    db_path = settings.db_path

    start = time.monotonic()
    logger.info("pipeline start: docket=%s", docket_id)

    if not args.skip_ingest:
        if not settings.regulations_gov_api_key:
            logger.error("REGULATIONS_GOV_API_KEY is required for ingestion")
            sys.exit(1)
        _ingest(docket_id, data_dir, settings.regulations_gov_api_key)
    else:
        pq = data_dir / "comments" / f"docket_id={docket_id}" / "part-00000.parquet"
        if not pq.exists():
            logger.error("--skip-ingest but no Parquet at %s", pq)
            sys.exit(1)
        logger.info("skipping ingest, using existing Parquet")

    _process(data_dir, docket_id)
    _citations(data_dir, docket_id)
    _dedup(data_dir, docket_id)
    _embed(data_dir, docket_id)
    _cluster(data_dir, docket_id, args.min_cluster_size)

    if not args.skip_label:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set, skipping cluster labeling")
        else:
            _label(data_dir, docket_id)
    else:
        logger.info("skipping LLM labeling")

    _load_db(data_dir, docket_id, db_path)

    elapsed = time.monotonic() - start
    logger.info("pipeline complete in %.1fs", elapsed)


if __name__ == "__main__":
    main()
