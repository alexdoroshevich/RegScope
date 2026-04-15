"""Parquet writer for raw Regulations.gov comments, partitioned by docket."""

from __future__ import annotations

import logging
import shutil
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

from data.ingest.raw_schema import RAW_COMMENT_COLUMNS, validate_raw_comments

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from data.ingest.regulations_gov import NormalizedComment

logger = logging.getLogger(__name__)


def write_comments_parquet(
    comments: Iterable[NormalizedComment],
    *,
    data_dir: Path,
    docket_id: str,
    fetched_at: datetime | None = None,
) -> Path:
    """Write ``comments`` to ``data_dir/comments/docket_id=<docket_id>/part-00000.parquet``.

    Idempotent: any existing partition for ``docket_id`` is replaced atomically.
    Validates output against :data:`RAW_COMMENT_SCHEMA` before writing.
    """
    if not docket_id:
        raise ValueError("docket_id is required")

    stamp = fetched_at or datetime.now(UTC)
    rows: list[dict[str, object]] = [
        {**asdict(comment), "fetched_at": stamp} for comment in comments
    ]

    frame = pl.DataFrame(rows, schema=RAW_COMMENT_COLUMNS)
    validate_raw_comments(frame)

    partition_dir = data_dir / "comments" / f"docket_id={docket_id}"
    if partition_dir.exists():
        shutil.rmtree(partition_dir)
    partition_dir.mkdir(parents=True, exist_ok=True)

    out_path = partition_dir / "part-00000.parquet"
    frame.write_parquet(out_path, compression="snappy")
    logger.info("wrote %d comments to %s", frame.height, out_path)
    return out_path
