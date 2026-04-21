"""Tests for API routes — comments, clusters, astroturf, and documents endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from api.deps import get_db
from api.main import app
from db.init_db import connect

if TYPE_CHECKING:
    from collections.abc import Generator

    import duckdb


@pytest.fixture()
def db() -> Generator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with schema applied."""
    conn = connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture()
def seeded_db(db: duckdb.DuckDBPyConnection) -> duckdb.DuckDBPyConnection:
    """DB with sample data for all three tables."""
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


@pytest.fixture()
def client(seeded_db: duckdb.DuckDBPyConnection) -> Generator[TestClient]:
    """TestClient with DuckDB dependency overridden to use seeded in-memory DB."""

    def _override_db() -> Generator[duckdb.DuckDBPyConnection]:
        yield seeded_db

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestCommentEndpoints:
    def test_list_comments(self, client: TestClient) -> None:
        resp = client.get("/api/v1/comments/DOC-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 4
        assert len(body["items"]) == 4
        assert body["limit"] == 100
        assert body["offset"] == 0

    def test_list_comments_pagination(self, client: TestClient) -> None:
        resp = client.get("/api/v1/comments/DOC-001?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 4

    def test_list_comments_empty_docket(self, client: TestClient) -> None:
        resp = client.get("/api/v1/comments/DOC-NONE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_list_comments_invalid_limit(self, client: TestClient) -> None:
        resp = client.get("/api/v1/comments/DOC-001?limit=0")
        assert resp.status_code == 422

    def test_list_comments_fields(self, client: TestClient) -> None:
        resp = client.get("/api/v1/comments/DOC-002")
        body = resp.json()
        item = body["items"][0]
        assert item["comment_id"] == "C-4"
        assert item["docket_id"] == "DOC-002"
        assert item["submitter_name"] == "Dave"


class TestClusterEndpoints:
    def test_list_clusters(self, client: TestClient) -> None:
        resp = client.get("/api/v1/clusters/DOC-001")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        cluster_ids = {c["cluster_id"] for c in body}
        assert cluster_ids == {0, 1}

    def test_list_clusters_empty_docket(self, client: TestClient) -> None:
        resp = client.get("/api/v1/clusters/DOC-NONE")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_cluster_comments(self, client: TestClient) -> None:
        resp = client.get("/api/v1/clusters/DOC-001/0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 3
        ids = {c["comment_id"] for c in body}
        assert ids == {"C-1", "C-3", "C-5"}

    def test_cluster_comments_empty(self, client: TestClient) -> None:
        resp = client.get("/api/v1/clusters/DOC-001/99")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAstroturfEndpoints:
    def test_list_groups(self, client: TestClient) -> None:
        resp = client.get("/api/v1/astroturf/groups")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2

    def test_list_groups_astroturf_only(self, client: TestClient) -> None:
        resp = client.get("/api/v1/astroturf/groups?astroturf_only=true")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["items"][0]["is_astroturf"] is True

    def test_list_groups_pagination(self, client: TestClient) -> None:
        resp = client.get("/api/v1/astroturf/groups?limit=1&offset=0")
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["limit"] == 1

    def test_summary(self, client: TestClient) -> None:
        resp = client.get("/api/v1/astroturf/summary")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_groups"] == 2
        assert body["astroturf_groups"] == 1
        assert body["max_campaign_likelihood"] == 6.0

    def test_group_fields(self, client: TestClient) -> None:
        resp = client.get("/api/v1/astroturf/groups?astroturf_only=true")
        group = resp.json()["items"][0]
        assert group["group_size"] == 6
        assert group["unique_submitters"] == 1
        assert group["template_text"] == "spam"
        assert len(group["comment_ids"]) == 6


# ---------------------------------------------------------------------------
# Documents fixture helper
# ---------------------------------------------------------------------------


def _insert_documents(db: duckdb.DuckDBPyConnection) -> None:
    from datetime import UTC, datetime

    stamp = datetime(2024, 6, 1, tzinfo=UTC)
    db.executemany(
        """
        INSERT INTO documents (
            document_number, docket_id, title, doc_type, abstract,
            agency_names, publication_date, effective_on, comments_close_on,
            html_url, citation, significant, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "2024-00001",
                "DOC-001",
                "Rule A",
                "RULE",
                None,
                '["EPA"]',
                "2024-03-01",
                None,
                None,
                None,
                None,
                False,
                stamp,
            ),
            (
                "2024-00002",
                "DOC-001",
                "Proposed Rule B",
                "PRORULE",
                None,
                '["EPA"]',
                "2024-02-01",
                None,
                None,
                None,
                None,
                False,
                stamp,
            ),
            (
                "2024-00003",
                "DOC-002",
                "Notice C",
                "NOTICE",
                None,
                '["FCC"]',
                "2024-01-15",
                None,
                None,
                None,
                None,
                None,
                stamp,
            ),
        ],
    )


@pytest.fixture()
def docs_client(db: duckdb.DuckDBPyConnection) -> Generator[TestClient]:
    """TestClient with documents pre-loaded."""
    _insert_documents(db)

    def _override_db() -> Generator[duckdb.DuckDBPyConnection]:
        yield db

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestDocumentEndpoints:
    def test_list_all(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert len(body["items"]) == 3
        assert body["limit"] == 50
        assert body["offset"] == 0

    def test_filter_by_docket_id(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?docket_id=DOC-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert all(d["docket_id"] == "DOC-001" for d in body["items"])

    def test_filter_by_doc_type(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?doc_type=NOTICE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["doc_type"] == "NOTICE"

    def test_filter_combined(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?docket_id=DOC-001&doc_type=RULE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["document_number"] == "2024-00001"

    def test_empty_result(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?docket_id=DOC-NONE")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_pagination(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?limit=2&offset=0")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["total"] == 3

    def test_ordered_newest_first(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents")
        items = resp.json()["items"]
        dates = [i["publication_date"] for i in items if i["publication_date"]]
        assert dates == sorted(dates, reverse=True)

    def test_invalid_limit(self, docs_client: TestClient) -> None:
        assert docs_client.get("/api/v1/documents?limit=0").status_code == 422
        assert docs_client.get("/api/v1/documents?limit=101").status_code == 422

    def test_invalid_offset(self, docs_client: TestClient) -> None:
        assert docs_client.get("/api/v1/documents?offset=-1").status_code == 422

    def test_response_fields(self, docs_client: TestClient) -> None:
        resp = docs_client.get("/api/v1/documents?limit=1")
        doc = resp.json()["items"][0]
        for field in (
            "document_number",
            "docket_id",
            "title",
            "doc_type",
            "abstract",
            "agency_names",
            "publication_date",
            "effective_on",
            "comments_close_on",
            "html_url",
            "citation",
            "significant",
            "fetched_at",
        ):
            assert field in doc
