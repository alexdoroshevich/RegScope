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
# Each template pairs a duplicate-comment body with a (group_size,
# unique_submitters) target so the demo always surfaces the full range
# of astroturf likelihoods: two clear-cut campaigns and one benign
# repeat. Likelihood = size / unique_submitters; >5.0 is flagged as
# astroturf.
_TEMPLATE_TEXTS: list[tuple[str, int, int]] = [
    (
        "I strongly oppose this regulation because it will harm jobs in my community.",
        24,
        3,  # likelihood 8.0 — clear astroturf
    ),
    (
        "Please reconsider the proposed rule as it imposes undue burdens.",
        17,
        3,  # likelihood 5.67 — over the astroturf threshold
    ),
    (
        "This rule is necessary to protect our environment for future generations.",
        14,
        12,  # likelihood 1.17 — benign dup cluster, not astroturf
    ),
]
_FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Hank"]
_LAST_NAMES = ["Smith", "Jones", "Williams", "Brown", "Taylor", "Davis", "Wilson"]

# Plausible supporting clauses that make seed comments readable while still
# giving each comment enough unique text to survive MinHash deduplication.
_SUPPORTING_CLAUSES = [
    "This will disproportionately affect rural and low-income communities.",
    "The proposed timeline is not realistic for small businesses.",
    "We urge the agency to extend the public comment period.",
    "The evidence in the draft assessment does not justify this action.",
    "Similar rules in other states have produced measurable benefits.",
    "I respectfully request additional economic impact analysis.",
    "Enforcement mechanisms remain unclear in the current proposal.",
    "The cost-benefit ratio appears favourable when externalities are priced in.",
    "There are significant compliance gaps for mid-sized operators.",
    "Stakeholders need more guidance on the transition provisions.",
    "Public health data published since 2018 supports a stronger rule.",
    "We support the intent but question the selected metrics.",
    "The rule should include a phase-in for existing facilities.",
    "Without exemptions for legacy equipment the rule is unworkable.",
    "An independent review of the modelling assumptions is warranted.",
]
_CFR_CITATIONS = [
    ("40 CFR Part 60", "CFR", 40, 60),
    ("40 CFR Part 63", "CFR", 40, 63),
    ("40 CFR Part 98", "CFR", 40, 98),
    ("42 CFR Part 73", "CFR", 42, 73),
    ("5 U.S.C. § 553", "USC", 5, 553),
    ("5 U.S.C. § 706", "USC", 5, 706),
]


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
        # 1-3 plausible supporting sentences; enough variety for MinHash to
        # still see each comment as distinct.
        clauses = rng.sample(_SUPPORTING_CLAUSES, k=rng.randint(1, 3))
        body = f"{topic}. {' '.join(clauses)}"
        rows.append(
            {
                "comment_id": _random_id("CMT"),
                "docket_id": _DOCKET_ID,
                "posted_date": posted.strftime("%Y-%m-%d"),
                "submitter_name": f"{first} {last}",
                "comment_text": body,
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

    for template, size, unique_submitters in _TEMPLATE_TEXTS:
        available = [cid for cid in all_ids if cid not in used]
        if len(available) < size:
            break
        group_ids = rng.sample(available, size)
        used.update(group_ids)
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


def _make_citations(comments_df: pl.DataFrame, rng: random.Random) -> pl.DataFrame:
    """Assign a random subset of comments synthetic CFR/USC citations."""
    rows = []
    for comment_id in comments_df["comment_id"].to_list():
        if rng.random() < 0.3:  # ~30% of comments reference a regulation
            text, ctype, ctitle, cpart = rng.choice(_CFR_CITATIONS)
            rows.append(
                {
                    "comment_id": comment_id,
                    "docket_id": _DOCKET_ID,
                    "citation_text": text,
                    "citation_type": ctype,
                    "cfr_title": ctitle,
                    "cfr_part": cpart,
                }
            )
    return pl.DataFrame(
        rows if rows else [],
        schema={
            "comment_id": pl.String,
            "docket_id": pl.String,
            "citation_text": pl.String,
            "citation_type": pl.String,
            "cfr_title": pl.Int32,
            "cfr_part": pl.Int32,
        },
    )


def _make_embeddings(comments_df: pl.DataFrame) -> pl.DataFrame:
    """Compute real sentence-transformer embeddings for the seed comments.

    Needed so the RAG ``/api/v1/query`` endpoint returns real results
    against the seed docket instead of the "No embedded comments found"
    fallback.  Takes a few seconds on CPU for the default 500 rows.
    """
    from nlp.embed import embed_comments

    logger.info("computing embeddings for %d seed comments", comments_df.height)
    return embed_comments(comments_df.select(["comment_id", "comment_text"]))


def seed(sample_size: int, data_dir: Path, db_path: Path) -> None:
    """Generate synthetic data and load it into DuckDB."""
    rng = random.Random(42)

    logger.info("generating %d synthetic comments for docket %s", sample_size, _DOCKET_ID)
    comments_df = _make_comments(sample_size, rng)
    groups_df = _make_duplicate_groups(comments_df, rng)
    clusters_df = _make_clusters(comments_df, rng)
    labels_df = _make_cluster_labels()
    citations_df = _make_citations(comments_df, rng)
    embeddings_df = _make_embeddings(comments_df)

    processed_dir = data_dir / "processed" / _DOCKET_ID
    processed_dir.mkdir(parents=True, exist_ok=True)

    comments_path = processed_dir / "comments.parquet"
    groups_path = processed_dir / "duplicate_groups.parquet"
    clusters_path = processed_dir / "clusters.parquet"
    labels_path = processed_dir / "cluster_labels.parquet"
    citations_path = processed_dir / "citations.parquet"
    embeddings_path = processed_dir / "embeddings.parquet"

    comments_df.write_parquet(comments_path, compression="snappy")
    groups_df.write_parquet(groups_path, compression="snappy")
    clusters_df.write_parquet(clusters_path, compression="snappy")
    labels_df.write_parquet(labels_path, compression="snappy")
    citations_df.write_parquet(citations_path, compression="snappy")
    embeddings_df.write_parquet(embeddings_path, compression="snappy")
    logger.info("wrote Parquet artefacts to %s", processed_dir)

    from db.init_db import (
        connect,
        load_citations,
        load_cluster_assignments,
        load_comments_parquet,
        load_duplicate_groups,
        load_embeddings,
    )
    from db.queries import upsert_cluster_label

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        load_comments_parquet(conn, str(comments_path))
        load_embeddings(conn, str(embeddings_path))
        load_duplicate_groups(conn, str(groups_path))
        load_cluster_assignments(conn, str(clusters_path))
        load_citations(conn, str(citations_path))
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
        help="Override FEDCOMMENT_DATA_DIR",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Override FEDCOMMENT_DB_PATH",
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
