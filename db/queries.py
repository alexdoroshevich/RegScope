"""Reusable DuckDB SQL queries for the API layer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import duckdb


def get_comments_by_docket(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Fetch comments for a docket with pagination."""
    result = conn.execute(
        """
        SELECT comment_id, docket_id, posted_date, submitter_name, comment_text
        FROM comments
        WHERE docket_id = ?
        ORDER BY comment_id
        LIMIT ? OFFSET ?
        """,
        [docket_id, limit, offset],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def count_comments_by_docket(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
) -> int:
    """Count total comments for a docket."""
    row = conn.execute(
        "SELECT COUNT(*) FROM comments WHERE docket_id = ?",
        [docket_id],
    ).fetchone()
    return int(row[0]) if row else 0


def get_duplicate_groups(
    conn: duckdb.DuckDBPyConnection,
    *,
    astroturf_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, object]]:
    """Fetch duplicate groups, optionally filtered to astroturf campaigns."""
    where = "WHERE is_astroturf = true" if astroturf_only else ""
    result = conn.execute(
        f"""
        SELECT group_id, comment_ids, group_size, unique_submitters,
               campaign_likelihood, is_astroturf, template_text
        FROM duplicate_groups
        {where}
        ORDER BY campaign_likelihood DESC
        LIMIT ? OFFSET ?
        """,
        [limit, offset],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def get_clusters_by_docket(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
) -> list[dict[str, object]]:
    """Fetch cluster assignments for a docket."""
    result = conn.execute(
        """
        SELECT cc.cluster_id, COUNT(*) as comment_count
        FROM comment_clusters cc
        WHERE cc.docket_id = ?
        GROUP BY cc.cluster_id
        ORDER BY comment_count DESC
        """,
        [docket_id],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def get_cluster_comments(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
    cluster_id: int,
    *,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Fetch comments belonging to a specific cluster."""
    result = conn.execute(
        """
        SELECT c.comment_id, c.comment_text, c.submitter_name
        FROM comments c
        JOIN comment_clusters cc ON c.comment_id = cc.comment_id
        WHERE cc.docket_id = ? AND cc.cluster_id = ?
        LIMIT ?
        """,
        [docket_id, cluster_id, limit],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def get_astroturf_summary(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, object]:
    """Get summary stats for astroturf detection."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) as total_groups,
            SUM(CASE WHEN is_astroturf THEN 1 ELSE 0 END) as astroturf_groups,
            SUM(group_size) as total_flagged_comments,
            MAX(campaign_likelihood) as max_campaign_likelihood
        FROM duplicate_groups
        """
    ).fetchone()
    if not row:
        return {
            "total_groups": 0,
            "astroturf_groups": 0,
            "total_flagged_comments": 0,
            "max_campaign_likelihood": 0.0,
        }
    return {
        "total_groups": row[0],
        "astroturf_groups": row[1],
        "total_flagged_comments": row[2],
        "max_campaign_likelihood": float(row[3]) if row[3] else 0.0,
    }
