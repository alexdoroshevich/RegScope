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
    if astroturf_only:
        result = conn.execute(
            """
            SELECT group_id, comment_ids, group_size, unique_submitters,
                   campaign_likelihood, is_astroturf, template_text
            FROM duplicate_groups
            WHERE is_astroturf = true
            ORDER BY campaign_likelihood DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
    else:
        result = conn.execute(
            """
            SELECT group_id, comment_ids, group_size, unique_submitters,
                   campaign_likelihood, is_astroturf, template_text
            FROM duplicate_groups
            ORDER BY campaign_likelihood DESC
            LIMIT ? OFFSET ?
            """,
            [limit, offset],
        )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def count_duplicate_groups(
    conn: duckdb.DuckDBPyConnection,
    *,
    astroturf_only: bool = False,
) -> int:
    """Return total number of duplicate groups, optionally filtered to astroturf."""
    if astroturf_only:
        row = conn.execute(
            "SELECT COUNT(*) FROM duplicate_groups WHERE is_astroturf = true"
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM duplicate_groups").fetchone()
    return int(row[0]) if row else 0


def get_clusters_by_docket(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
) -> list[dict[str, object]]:
    """Fetch cluster summaries for a docket, including LLM labels when available."""
    result = conn.execute(
        """
        SELECT cc.cluster_id,
               COUNT(*) as comment_count,
               cl.label,
               cl.summary
        FROM comment_clusters cc
        LEFT JOIN cluster_labels cl
            ON cc.docket_id = cl.docket_id AND cc.cluster_id = cl.cluster_id
        WHERE cc.docket_id = ?
        GROUP BY cc.cluster_id, cl.label, cl.summary
        ORDER BY comment_count DESC
        """,
        [docket_id],
    )
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def upsert_cluster_label(
    conn: duckdb.DuckDBPyConnection,
    *,
    docket_id: str,
    cluster_id: int,
    label: str,
    summary: str,
    prompt_hash: str,
    model: str,
    cost_usd: float,
) -> None:
    """Insert or update a cluster label."""
    conn.execute(
        """
        INSERT OR REPLACE INTO cluster_labels
            (docket_id, cluster_id, label, summary, prompt_hash, model, cost_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [docket_id, cluster_id, label, summary, prompt_hash, model, cost_usd],
    )


def get_cluster_labels(
    conn: duckdb.DuckDBPyConnection,
    docket_id: str,
) -> list[dict[str, object]]:
    """Fetch all cluster labels for a docket."""
    result = conn.execute(
        """
        SELECT docket_id, cluster_id, label, summary, prompt_hash, model, cost_usd
        FROM cluster_labels
        WHERE docket_id = ?
        ORDER BY cluster_id
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


def get_comments_by_group(
    conn: duckdb.DuckDBPyConnection,
    group_id: int,
    *,
    limit: int = 50,
) -> list[dict[str, object]]:
    """Fetch comments belonging to a duplicate group via its stored comment_ids array."""
    result = conn.execute(
        """
        SELECT c.comment_id, c.comment_text, c.submitter_name
        FROM comments c
        WHERE c.comment_id IN (
            SELECT UNNEST(comment_ids)
            FROM duplicate_groups
            WHERE group_id = ?
        )
        LIMIT ?
        """,
        [group_id, limit],
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
