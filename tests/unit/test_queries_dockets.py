"""Unit tests for list_dockets / count_dockets query helpers."""

from __future__ import annotations

import duckdb
import pytest

from db.init_db import init_schema
from db.queries import count_dockets, list_dockets


@pytest.fixture()
def conn() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB seeded with two dockets."""
    c = duckdb.connect(":memory:")
    init_schema(c)
    c.execute(
        """
        INSERT INTO comments (comment_id, docket_id, posted_date, submitter_name, comment_text)
        VALUES
          ('C-001', 'EPA-2024-0001', '2024-01-01', 'Alice', 'comment one'),
          ('C-002', 'EPA-2024-0001', '2024-01-02', 'Bob',   'comment two'),
          ('C-003', 'EPA-2024-0001', '2024-01-03', 'Carol', 'comment three'),
          ('C-004', 'DOT-2024-9999', '2024-01-04', 'Dave',  'transport comment')
        """
    )
    return c


class TestListDockets:
    def test_returns_all_dockets_when_no_filter(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn)
        docket_ids = {r["docket_id"] for r in rows}
        assert docket_ids == {"EPA-2024-0001", "DOT-2024-9999"}

    def test_ordered_by_comment_count_desc(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn)
        assert rows[0]["docket_id"] == "EPA-2024-0001"
        assert rows[0]["comment_count"] == 3
        assert rows[1]["docket_id"] == "DOT-2024-9999"
        assert rows[1]["comment_count"] == 1

    def test_filter_by_q_substring(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn, q="EPA")
        assert len(rows) == 1
        assert rows[0]["docket_id"] == "EPA-2024-0001"

    def test_filter_is_case_insensitive(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn, q="epa")
        assert len(rows) == 1
        assert rows[0]["docket_id"] == "EPA-2024-0001"

    def test_filter_returns_empty_for_no_match(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn, q="NOMATCH")
        assert rows == []

    def test_limit_is_respected(self, conn: duckdb.DuckDBPyConnection) -> None:
        rows = list_dockets(conn, limit=1)
        assert len(rows) == 1

    def test_offset_paginates(self, conn: duckdb.DuckDBPyConnection) -> None:
        first = list_dockets(conn, limit=1, offset=0)
        second = list_dockets(conn, limit=1, offset=1)
        assert first[0]["docket_id"] != second[0]["docket_id"]


class TestCountDockets:
    def test_counts_all_dockets(self, conn: duckdb.DuckDBPyConnection) -> None:
        assert count_dockets(conn) == 2

    def test_count_with_matching_filter(self, conn: duckdb.DuckDBPyConnection) -> None:
        assert count_dockets(conn, q="EPA") == 1

    def test_count_with_no_match(self, conn: duckdb.DuckDBPyConnection) -> None:
        assert count_dockets(conn, q="NOMATCH") == 0

    def test_count_empty_db(self) -> None:
        empty = duckdb.connect(":memory:")
        init_schema(empty)
        assert count_dockets(empty) == 0
        empty.close()
