"""Unit tests for scripts/seed_data.py."""

from __future__ import annotations

import random


def test_make_comments_count() -> None:
    from scripts.seed_data import _make_comments

    rng = random.Random(0)
    df = _make_comments(50, rng)
    assert df.height == 50


def test_make_comments_schema() -> None:
    from scripts.seed_data import _make_comments

    rng = random.Random(0)
    df = _make_comments(10, rng)
    assert set(df.columns) >= {"comment_id", "docket_id", "comment_text", "submitter_name"}
    assert df["comment_id"].is_unique().all()


def test_make_duplicate_groups() -> None:
    from scripts.seed_data import _make_comments, _make_duplicate_groups

    rng = random.Random(0)
    comments = _make_comments(100, rng)
    groups = _make_duplicate_groups(comments, rng)
    assert groups.height > 0
    assert "campaign_likelihood" in groups.columns
    assert "is_astroturf" in groups.columns


def test_make_clusters_covers_all_comments() -> None:
    from scripts.seed_data import _make_clusters, _make_comments

    rng = random.Random(0)
    comments = _make_comments(30, rng)
    clusters = _make_clusters(comments, rng)
    assert clusters.height == 30
    assert set(clusters["comment_id"].to_list()) == set(comments["comment_id"].to_list())


def test_make_cluster_labels_deterministic() -> None:
    from scripts.seed_data import _make_cluster_labels

    df1 = _make_cluster_labels()
    df2 = _make_cluster_labels()
    assert df1.equals(df2)
    assert df1.height > 0


def test_seed_end_to_end(tmp_path: object) -> None:
    from pathlib import Path

    from scripts.seed_data import seed

    data_dir = Path(str(tmp_path)) / "data"
    db_path = Path(str(tmp_path)) / "test.db"
    seed(50, data_dir, db_path)

    import duckdb

    conn = duckdb.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM comments").fetchone()
    conn.close()
    assert count is not None and count[0] == 50
