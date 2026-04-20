"""Shared fixtures for integration tests — real DuckDB, real FastAPI TestClient."""

from __future__ import annotations

from typing import TYPE_CHECKING

import duckdb
import pytest
from fastapi.testclient import TestClient

from api.deps import get_db
from api.main import app
from db.init_db import init_schema

if TYPE_CHECKING:
    from collections.abc import Generator

_DOCKET = "EPA-HQ-OAR-2021-0317"


def _seed(conn: duckdb.DuckDBPyConnection) -> None:
    """Insert minimal rows covering all three MVP tables."""
    conn.execute(
        """
        INSERT INTO comments (comment_id, docket_id, posted_date, submitter_name, comment_text)
        VALUES
          ('C-001', ?, '2024-01-01', 'Alice',   'Please strengthen the clean-air rule.'),
          ('C-002', ?, '2024-01-02', 'Bob',     'Please strengthen the clean-air rule.'),
          ('C-003', ?, '2024-01-03', 'Charlie', 'I oppose this regulation entirely.'),
          ('C-004', 'OTHER-DOCKET', '2024-01-04', 'Dana', 'Unrelated comment.')
        """,
        [_DOCKET, _DOCKET, _DOCKET],
    )
    conn.execute(
        """
        INSERT INTO duplicate_groups
          (group_id, comment_ids, group_size, unique_submitters, campaign_likelihood, is_astroturf, template_text)
        VALUES
          (1, ['C-001','C-002'], 2, 2, 1.0,  true,  'Please strengthen the clean-air rule.'),
          (2, ['C-003'],        1, 1, 0.2,  false, 'I oppose this regulation entirely.')
        """
    )
    conn.execute(
        """
        INSERT INTO comment_clusters (comment_id, docket_id, cluster_id)
        VALUES
          ('C-001', ?, 0),
          ('C-002', ?, 0),
          ('C-003', ?, 1)
        """,
        [_DOCKET, _DOCKET, _DOCKET],
    )
    conn.execute(
        """
        INSERT INTO cluster_labels (docket_id, cluster_id, label, summary, prompt_hash, model, cost_usd)
        VALUES (?, 0, 'Clean air support', 'Comments supporting clean-air rules.', 'abc123', 'gpt-4o-mini', 0.001)
        """,
        [_DOCKET],
    )
    conn.execute(
        """
        INSERT INTO citations (comment_id, docket_id, citation_text, citation_type, cfr_title, cfr_part)
        VALUES
          ('C-001', ?, '40 CFR Part 60', 'CFR', 40, 60),
          ('C-002', ?, '40 CFR Part 60', 'CFR', 40, 60),
          ('C-003', ?, '5 U.S.C. § 553',  'USC',  5, 553)
        """,
        [_DOCKET, _DOCKET, _DOCKET],
    )
    # Seed unit-norm embeddings so RAG similarity search returns real results.
    import numpy as np

    rng = np.random.default_rng(42)
    for cid in ("C-001", "C-002", "C-003"):
        vec = rng.standard_normal(384).astype(np.float32)
        vec /= np.linalg.norm(vec)
        conn.execute(
            "UPDATE comments SET embedding = ? WHERE comment_id = ?",
            [vec.tolist(), cid],
        )


@pytest.fixture()
def db_conn() -> Generator[duckdb.DuckDBPyConnection]:
    """In-memory DuckDB with schema and seed data, torn down after each test."""
    conn = duckdb.connect(":memory:")
    init_schema(conn)
    _seed(conn)
    yield conn
    conn.close()


@pytest.fixture()
def api_client(db_conn: duckdb.DuckDBPyConnection) -> Generator[TestClient]:
    """FastAPI TestClient with get_db overridden to use the seeded in-memory DB."""

    def _override() -> Generator[duckdb.DuckDBPyConnection]:
        yield db_conn

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
