"""Tests for db/ — DuckDB schema, initialization, and queries."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl
import pytest

if TYPE_CHECKING:
    import duckdb

from db.init_db import connect, init_schema, load_comments_parquet, load_documents
from db.queries import (
    count_comments_by_docket,
    count_documents,
    get_astroturf_summary,
    get_cluster_comments,
    get_cluster_labels,
    get_clusters_by_docket,
    get_comments_by_docket,
    get_document,
    get_duplicate_groups,
    list_documents,
    upsert_cluster_label,
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
        assert "cluster_labels" in table_names

    def test_idempotent_schema(self, db: duckdb.DuckDBPyConnection) -> None:
        init_schema(db)
        tables = db.execute("SHOW TABLES").fetchall()
        assert (
            len(tables) == 6
        )  # comments, duplicate_groups, comment_clusters, cluster_labels, citations, documents


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

    def test_get_clusters_includes_labels(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        upsert_cluster_label(
            seeded_db,
            docket_id="DOC-001",
            cluster_id=0,
            label="Support",
            summary="Comments supporting the rule",
            prompt_hash="abc",
            model="gpt-4o-mini",
            cost_usd=0.001,
        )
        results = get_clusters_by_docket(seeded_db, "DOC-001")
        labeled = next(r for r in results if r["cluster_id"] == 0)
        assert labeled["label"] == "Support"
        assert labeled["summary"] == "Comments supporting the rule"

    def test_get_clusters_without_labels(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        results = get_clusters_by_docket(seeded_db, "DOC-001")
        for r in results:
            assert r["label"] is None

    def test_upsert_cluster_label(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        upsert_cluster_label(
            seeded_db,
            docket_id="DOC-001",
            cluster_id=0,
            label="V1",
            summary="First version",
            prompt_hash="h1",
            model="gpt-4o-mini",
            cost_usd=0.001,
        )
        upsert_cluster_label(
            seeded_db,
            docket_id="DOC-001",
            cluster_id=0,
            label="V2",
            summary="Updated version",
            prompt_hash="h2",
            model="gpt-4o-mini",
            cost_usd=0.002,
        )
        labels = get_cluster_labels(seeded_db, "DOC-001")
        assert len(labels) == 1
        assert labels[0]["label"] == "V2"

    def test_get_cluster_labels_empty(self, seeded_db: duckdb.DuckDBPyConnection) -> None:
        labels = get_cluster_labels(seeded_db, "DOC-999")
        assert labels == []


# ---------------------------------------------------------------------------
# Helper: minimal document row dict
# ---------------------------------------------------------------------------


def _doc_row(
    *,
    num: int = 1,
    docket_id: str | None = "EPA-HQ-OAR-2024-0001",
    doc_type: str = "RULE",
) -> dict[str, object]:
    from datetime import UTC, datetime

    return {
        "document_number": f"2024-{num:05d}",
        "docket_id": docket_id,
        "title": f"Test Rule {num}",
        "doc_type": doc_type,
        "abstract": None,
        "agency_names": '["EPA"]',
        "publication_date": f"2024-03-{num:02d}",
        "effective_on": None,
        "comments_close_on": None,
        "html_url": None,
        "citation": None,
        "significant": False,
        "fetched_at": datetime(2024, 6, 1, tzinfo=UTC),
    }


class TestLoadDocuments:
    def test_load_from_parquet(self, db: duckdb.DuckDBPyConnection, tmp_path: object) -> None:
        from pathlib import Path

        import polars as pl

        from data.ingest.federal_register import DOCUMENT_COLUMNS

        tmp = Path(str(tmp_path))
        df = pl.DataFrame([_doc_row(num=1), _doc_row(num=2)], schema=DOCUMENT_COLUMNS)
        pq_path = tmp / "docs.parquet"
        df.write_parquet(pq_path)

        count = load_documents(db, str(pq_path))
        assert count == 2
        rows = db.execute("SELECT COUNT(*) FROM documents").fetchone()
        assert rows[0] == 2  # type: ignore[index]

    def test_load_is_idempotent(self, db: duckdb.DuckDBPyConnection, tmp_path: object) -> None:
        """Loading the same Parquet twice should not duplicate rows."""
        from pathlib import Path

        import polars as pl

        from data.ingest.federal_register import DOCUMENT_COLUMNS

        tmp = Path(str(tmp_path))
        df = pl.DataFrame([_doc_row(num=1)], schema=DOCUMENT_COLUMNS)
        pq_path = tmp / "docs.parquet"
        df.write_parquet(pq_path)

        load_documents(db, str(pq_path))
        load_documents(db, str(pq_path))
        rows = db.execute("SELECT COUNT(*) FROM documents").fetchone()
        assert rows[0] == 1  # type: ignore[index]

    def test_load_replaces_existing(self, db: duckdb.DuckDBPyConnection, tmp_path: object) -> None:
        """Re-loading with updated title replaces the row (INSERT OR REPLACE)."""
        from pathlib import Path

        import polars as pl

        from data.ingest.federal_register import DOCUMENT_COLUMNS

        tmp = Path(str(tmp_path))
        row = _doc_row(num=1)
        df1 = pl.DataFrame([row], schema=DOCUMENT_COLUMNS)
        pq1 = tmp / "docs_v1.parquet"
        df1.write_parquet(pq1)
        load_documents(db, str(pq1))

        updated = {**row, "title": "Updated Title"}
        df2 = pl.DataFrame([updated], schema=DOCUMENT_COLUMNS)
        pq2 = tmp / "docs_v2.parquet"
        df2.write_parquet(pq2)
        load_documents(db, str(pq2))

        result = db.execute(
            "SELECT title FROM documents WHERE document_number = '2024-00001'"
        ).fetchone()
        assert result is not None
        assert result[0] == "Updated Title"


class TestDocumentQueries:
    @pytest.fixture()
    def doc_db(self, db: duckdb.DuckDBPyConnection, tmp_path: object) -> duckdb.DuckDBPyConnection:
        """DB pre-loaded with a handful of FR documents."""
        from pathlib import Path

        import polars as pl

        from data.ingest.federal_register import DOCUMENT_COLUMNS

        tmp = Path(str(tmp_path))
        rows = [
            _doc_row(num=1, docket_id="EPA-HQ-OAR-2024-0001", doc_type="RULE"),
            _doc_row(num=2, docket_id="EPA-HQ-OAR-2024-0001", doc_type="PRORULE"),
            _doc_row(num=3, docket_id="EPA-HQ-OAR-2024-0002", doc_type="RULE"),
            _doc_row(num=4, docket_id=None, doc_type="NOTICE"),
        ]
        df = pl.DataFrame(rows, schema=DOCUMENT_COLUMNS)
        pq = tmp / "docs.parquet"
        df.write_parquet(pq)
        load_documents(db, str(pq))
        return db

    def test_list_all_documents(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        results = list_documents(doc_db)
        assert len(results) == 4

    def test_list_documents_filter_docket(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        results = list_documents(doc_db, docket_id="EPA-HQ-OAR-2024-0001")
        assert len(results) == 2
        assert all(r["docket_id"] == "EPA-HQ-OAR-2024-0001" for r in results)

    def test_list_documents_filter_doc_type(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        results = list_documents(doc_db, doc_type="RULE")
        assert len(results) == 2
        assert all(r["doc_type"] == "RULE" for r in results)

    def test_list_documents_pagination(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        page1 = list_documents(doc_db, limit=2, offset=0)
        page2 = list_documents(doc_db, limit=2, offset=2)
        assert len(page1) == 2
        assert len(page2) == 2
        ids1 = {r["document_number"] for r in page1}
        ids2 = {r["document_number"] for r in page2}
        assert ids1.isdisjoint(ids2)

    def test_count_documents_all(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        assert count_documents(doc_db) == 4

    def test_count_documents_filter(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        assert count_documents(doc_db, docket_id="EPA-HQ-OAR-2024-0002") == 1
        assert count_documents(doc_db, doc_type="NOTICE") == 1

    def test_get_document_found(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        doc = get_document(doc_db, "2024-00001")
        assert doc is not None
        assert doc["title"] == "Test Rule 1"
        assert doc["doc_type"] == "RULE"

    def test_get_document_not_found(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        doc = get_document(doc_db, "9999-99999")
        assert doc is None

    def test_list_documents_combined_filters(self, doc_db: duckdb.DuckDBPyConnection) -> None:
        results = list_documents(doc_db, docket_id="EPA-HQ-OAR-2024-0001", doc_type="PRORULE")
        assert len(results) == 1
        assert results[0]["document_number"] == "2024-00002"
