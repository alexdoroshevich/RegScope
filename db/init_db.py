"""DuckDB initialization and Parquet loading."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATION_DIR = "db/migrations"


def _read_migration(name: str) -> str:
    """Read a SQL migration file from the migrations directory."""
    from pathlib import Path

    path = Path(_MIGRATION_DIR) / name
    return path.read_text(encoding="utf-8")


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply all migrations to create the schema."""
    from pathlib import Path

    migration_dir = Path(_MIGRATION_DIR)
    if not migration_dir.exists():
        logger.warning("migration directory %s does not exist", _MIGRATION_DIR)
        return

    migrations = sorted(migration_dir.glob("*.sql"))
    for migration in migrations:
        logger.info("applying migration %s", migration.name)
        conn.execute(migration.read_text(encoding="utf-8"))


def connect(db_path: str | Path = ":memory:") -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection and apply schema migrations."""
    conn = duckdb.connect(str(db_path))
    init_schema(conn)
    return conn


def load_comments_parquet(
    conn: duckdb.DuckDBPyConnection,
    parquet_glob: str,
) -> int:
    """Load raw comment Parquet files into the comments table.

    Returns the number of rows loaded from the Parquet file.
    """
    count_row = conn.execute("SELECT COUNT(*) FROM read_parquet(?)", [parquet_glob]).fetchone()
    count = int(count_row[0]) if count_row else 0
    conn.execute(
        """
        INSERT OR IGNORE INTO comments (
            comment_id, docket_id, posted_date,
            submitter_name, comment_text, fetched_at
        )
        SELECT
            comment_id, docket_id, posted_date,
            submitter_name, comment_text, fetched_at
        FROM read_parquet(?)
        """,
        [parquet_glob],
    )
    logger.info("loaded %d comments from %s", count, parquet_glob)
    return count


def load_duplicate_groups(
    conn: duckdb.DuckDBPyConnection,
    groups_parquet: str,
) -> int:
    """Load duplicate-group results from Parquet into the duplicate_groups table."""
    count_row = conn.execute("SELECT COUNT(*) FROM read_parquet(?)", [groups_parquet]).fetchone()
    count = int(count_row[0]) if count_row else 0
    conn.execute(
        """
        INSERT OR REPLACE INTO duplicate_groups
        SELECT * FROM read_parquet(?)
        """,
        [groups_parquet],
    )
    logger.info("loaded %d duplicate groups from %s", count, groups_parquet)
    return count


def load_cluster_assignments(
    conn: duckdb.DuckDBPyConnection,
    clusters_parquet: str,
) -> int:
    """Load cluster assignments from Parquet into the comment_clusters table."""
    count_row = conn.execute("SELECT COUNT(*) FROM read_parquet(?)", [clusters_parquet]).fetchone()
    count = int(count_row[0]) if count_row else 0
    conn.execute(
        """
        INSERT OR REPLACE INTO comment_clusters
        SELECT * FROM read_parquet(?)
        """,
        [clusters_parquet],
    )
    logger.info("loaded %d cluster assignments from %s", count, clusters_parquet)
    return count
