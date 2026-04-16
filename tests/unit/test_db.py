"""Tests for db/ — DuckDB schema, initialization, and queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
import pytest

if TYPE_CHECKING:
    import duckdb

from db.init_db import connect, init_schema, load_comments_parquet
from db.queries import (
    count_comments_by_docket,
    get_astroturf_summary,
    get_cluster_comments,
    get_clusters_by_docket,
    get_comments_by_docket,
    get_duplicate_groups,
)


@pytest.fixture()
def db() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with schema applied."""
    conn = connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def seeded_db(db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    """DB with sample comments, duplicate groups, and cluster assignments."""
    db.executemany(
        """
        INSERT INTO comments (comment_id, docket_id, posted_date, submitter_name, comment_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("C-1", "DOC-001", "2024-01-01", "Alice", "I support this rule"),
            ("C-2", "DOC-001", "2024-01-02", "Bob", "I oppose this rule"),
            ("C-3", "DOC-001", "2024-01-03", "Carol", "I support this rule"),
            ("C-4", "DOC-002", "2024-01-04", "Dave", "Different docket comment"),
            ("C-5", "DOC-001", "2024-01-05", "Eve", "Another support comment"),
        ],
    )
    db.executemany(
        """
        INSERT INTO duplicate_groups
            (group_id, comment_ids, group_size, unique_submitters,
             campaign_likelihood, is_astroturf, template_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (0, ["C-1", "C-3"], 2, 2, 1.0, False, "I support this rule"),
            (1, ["C-10", "C-11", "C-12", "C-13", "C-14", "C-15"], 6, 1, 6.0, True, "spam"),
        ],
    )
    db.executemany(
        "INSERT INTO comment_clusters (comment_id, docket_id, cluster_id) VALUES (?, ?, ?)",
        [
            ("C-1", "DOC-001", 0),
            ("C-3", "DOC-001", 0),
            ("C-5", "DOC-001", 0),
            ("C-2", "DOC-001", 1),
        ],
    )
    return db


class TestSchema:
    def test_tables_created(self, db: duckdb.DuckDBPyConnection) -> None:
        tables = db.execute("SHOW TABLES").fetchall()
        table_names = {t[0] for t in tables}
        assert "comments" in table_names
        assert "duplicate_groups" in table_names
        assert "comment_clusters" in table_names

    def test_idempotent_schema(self, db: duckdb.DuckDBPyConnection) -> None:
        init_schema(db)
        tables = db.execute("SHOW TABLES").fetchall()
        assert len(tables) == 3


class TestLoadCommentsParquet:
    def test_load_from_parquet(self, db: duckdb.DuckDBPyConnection, tmp_path: object) -> None:
        from pathlib import Path

        tmp = Path(str(tmp_path))
        df = pl.DataFrame(
            {
                "comment_id": ["P-1", "P-2"],
                "docket_id": ["DOC-X", "DOC-X"],
                "posted_date": ["2024-01-01", "2024-01-02"],
                "submitter_name": ["A", "B"],
                "comment_text": ["hello", "world"],
                "fetched_at": [None, None],
            }
        )
        pq_path = tmp / "test.parquet"
        df.write_parquet(pq_path)
        count = load_comments_parquet(db, str(pq_path))
        assert count == 2
        rows = db.execute("SELECT COUNT(*) FROM comments").fetchone()
        assert rows[0] == 2  # type: ignore[index]


class TestQueries:
    def test_get_comments_by_docket(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        results = get_comments_by_docket(seeded_db, "DOC-001")
        assert len(results) == 4
        assert all(r["docket_id"] == "DOC-001" for r in results)

    def test_get_comments_pagination(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        page1 = get_comments_by_docket(seeded_db, "DOC-001", limit=2, offset=0)
        page2 = get_comments_by_docket(seeded_db, "DOC-001", limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids_1 = {r["comment_id"] for r in page1}
        ids_2 = {r["comment_id"] for r in page2}
        assert ids_1.isdisjoint(ids_2)

    def test_count_comments_by_docket(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        assert count_comments_by_docket(seeded_db, "DOC-001") == 4
        assert count_comments_by_docket(seeded_db, "DOC-002") == 1
        assert count_comments_by_docket(seeded_db, "DOC-NONE") == 0

    def test_get_duplicate_groups_all(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        results = get_duplicate_groups(seeded_db)
        assert len(results) == 2

    def test_get_duplicate_groups_astroturf_only(
        self, seeded_db: duckdb.DuckDBPyConnection
    ) -> None:
        results = get_duplicate_groups(seeded_db, astroturf_only=True)
        assert len(results) == 1
        assert results[0]["is_astroturf"] is True
        assert results[0]["campaign_likelihood"] == 6.0

    def test_get_clusters_by_docket(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        results = get_clusters_by_docket(seeded_db, "DOC-001")
        assert len(results) == 2
        cluster_ids = {r["cluster_id"] for r in results}
        assert cluster_ids == {0, 1}

    def test_get_cluster_comments(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        results = get_cluster_comments(seeded_db, "DOC-001", 0)
        assert len(results) == 3
        ids = {r["comment_id"] for r in results}
        assert ids == {"C-1", "C-3", "C-5"}

    def test_get_astroturf_summary(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        summary = get_astroturf_summary(seeded_db)
        assert summary["total_groups"] == 2
        assert summary["astroturf_groups"] == 1
        assert summary["max_campaign_likelihood"] == 6.0
