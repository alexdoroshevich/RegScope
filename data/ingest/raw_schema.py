"""Schema spec for raw Regulations.gov comment rows written to Parquet."""

from __future__ import annotations

import polars as pl

from data.validation import validate

RAW_COMMENT_COLUMNS: dict[str, pl.DataType] = {
    "comment_id": pl.String(),
    "docket_id": pl.String(),
    "posted_date": pl.String(),
    "submitter_name": pl.String(),
    "comment_text": pl.String(),
    "fetched_at": pl.Datetime(time_unit="us", time_zone="UTC"),
}


def validate_raw_comments(frame: pl.DataFrame) -> None:
    """Validate a raw-comments DataFrame before writing to Parquet."""
    validate(
        frame,
        required=RAW_COMMENT_COLUMNS,
        unique=("comment_id",),
        non_null=("comment_id", "docket_id", "fetched_at"),
        strict=True,
    )
