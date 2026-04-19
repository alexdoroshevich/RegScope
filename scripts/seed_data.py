"""Generate synthetic sample data for local development.

Usage:
    uv run python scripts/seed_data.py --sample-size 500

Writes Parquet files under data/ and loads them into DuckDB so the API
and frontend work without a real Regulations.gov API key.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import random
import string
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

_DOCKET_ID = "DEMO-2024-0001"
_CLUSTER_TOPICS = [
    "Environmental impact concerns",
    "Economic burden on small businesses",
    "Public health implications",
    "Compliance timeline is too aggressive",
    "Support for stricter enforcement",
    "Request for extended comment period",
]
_TEMPLATE_TEXTS = [
    "I strongly oppose this regulation because it will harm jobs in my community.",
    "Please reconsider the proposed rule as it imposes undue burdens.",
    "This rule is necessary to protect our environment for future generations.",
]
_FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank"]
_LAST_NAMES = ["Smith", "Jones", "Williams", "Brown", "Taylor", "Davis", "Wilson"]


def _random_id(prefix: str = "CMS") -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}-{suffix}"


def _make_comments(n: int, rng: random.Random) -> pl.DataFrame:
    """Generate n synthetic comments."""
    base_date = datetime(2024, 1, 1, tzinfo=UTC)
    rows = []
    for _ in range(n):
        days_offset = rng.randint(0, 180)
        posted = base_date + timedelta(days=days_offset)
        first = rng.choice(_FIRST_NAMES)
        last = rng.choice(_LAST_NAMES)
        topic = rng.choice(_CLUSTER_TOPICS)
        extra = " ".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(5, 20)))
        rows.append(
            {
                "comment_id": _random_id("CMT"),
                "docket_id": _DOCKET_ID,
                "posted_date": posted.strftime("%Y-%m-%d"),
                "submitter_name": f"{first} {last}",
                "comment_text": f"{topic}. {extra}",
                "fetched_at": datetime.now(UTC),
            }
        )
    return pl.DataFrame(rows)


def _make_duplicate_groups(comments_df: pl.DataFrame, rng: random.Random) -> pl.DataFrame:
    """Create a small set of synthetic duplicate groups from existing comment IDs."""
    all_ids: list[str] = comments_df["comment_id"].to_list()
    groups = []
    used: set[str] = set()
    group_id = 1

    for template in _TEMPLATE_TEXTS:
        size = rng.randint(8, 20)
        available = [cid for cid in all_ids if cid not in used]
        if len(available) < size:
            break
        group_ids = rng.sample(available, size)
        used.update(group_ids)
        unique_submitters = max(1, rng.randint(1, size - 1))
        likelihood = round(size / unique_submitters, 4)
        groups.append(
            {
                "group_id": group_id,
                "comment_ids": group_ids,
                "group_size": size,
                "unique_submitters": unique_submitters,
                "campaign_likelihood": likelihood,
                "is_astroturf": likelihood > 5.0,
                "template_text": template,
            }
        )
        group_id += 1

    return pl.DataFrame(
        groups,
        schema={
            "group_id": pl.Int32,
            "comment_ids": pl.List(pl.String),
            "group_size": pl.Int32,
            "unique_submitters": pl.Int32,
            "campaign_likelihood": pl.Float64,
            "is_astroturf": pl.Boolean,
            "template_text": pl.String,
        },
    )


def _make_clusters(comments_df: pl.DataFrame, rng: random.Random) -> pl.DataFrame:
    """Assign each comment to a cluster (0-based, -1 for noise)."""
    n_clusters = len(_CLUSTER_TOPICS)
    rows = []
    for comment_id in comments_df["comment_id"].to_list():
        roll = rng.random()
        cluster_id = -1 if roll < 0.05 else rng.randint(0, n_clusters - 1)
        rows.append(
            {
                "comment_id": comment_id,
                "docket_id": _DOCKET_ID,
                "cluster_id": cluster_id,
            }
        )
    return pl.DataFrame(rows)


def _make_cluster_labels() -> pl.DataFrame:
    """Generate deterministic LLM-style labels for each cluster."""
    rows = []
    for idx, topic in enumerate(_CLUSTER_TOPICS):
        prompt = f"Label cluster {idx}: {topic}"
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]
        rows.append(
            {
                "docket_id": _DOCKET_ID,
                "cluster_id": idx,
                "label": topic,
                "summary": f"Comments expressing: {topic.lower()}.",
                "prompt_hash": prompt_hash,
                "model": "gpt-4o-mini",
                "cost_usd": 0.0002,
            }
        )
    return pl.DataFrame(rows)


def seed(sample_size: int, data_dir: Path, db_path: Path) -> None:
    """Generate synthetic data and load it into DuckDB."""
    rng = random.Random(42)

    logger.info("generating %d synthetic comments for docket %s", sample_size, _DOCKET_ID)
    comments_df = _make_comments(sample_size, rng)
    groups_df = _make_duplicate_groups(comments_df, rng)
    clusters_df = _make_clusters(comments_df, rng)
    labels_df = _make_cluster_labels()

    processed_dir = data_dir / "processed" / _DOCKET_ID
    processed_dir.mkdir(parents=True, exist_ok=True)

    comments_path = processed_dir / "comments.parquet"
    groups_path = processed_dir / "duplicate_groups.parquet"
    clusters_path = processed_dir / "clusters.parquet"
    labels_path = processed_dir / "cluster_labels.parquet"

    comments_df.write_parquet(comments_path, compression="snappy")
    groups_df.write_parquet(groups_path, compression="snappy")
    clusters_df.write_parquet(clusters_path, compression="snappy")
    labels_df.write_parquet(labels_path, compression="snappy")
    logger.info("wrote Parquet artefacts to %s", processed_dir)

    from db.init_db import (
        connect,
        load_cluster_assignments,
        load_comments_parquet,
        load_duplicate_groups,
    )
    from db.queries import upsert_cluster_label

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        load_comments_parquet(conn, str(comments_path))
        load_duplicate_groups(conn, str(groups_path))
        load_cluster_assignments(conn, str(clusters_path))
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
        logger.info("loaded all artefacts into %s", db_path)
    finally:
        conn.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed DuckDB with synthetic sample data.")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=500,
        help="Number of synthetic comments to generate (default: 500)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override REGSCOPE_DATA_DIR",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Override REGSCOPE_DB_PATH",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv)

    from api.config import get_settings

    settings = get_settings()
    data_dir = args.data_dir or settings.data_dir
    db_path = args.db_path or settings.db_path

    if args.sample_size < 1:
        logger.error("--sample-size must be at least 1")
        sys.exit(1)

    seed(args.sample_size, data_dir, db_path)
    logger.info("seed complete")


if __name__ == "__main__":
    main()
