"""Clean and normalise raw comment Parquet, writing validated processed output."""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

from data.ingest.raw_schema import RAW_COMMENT_COLUMNS
from data.validation import validate

logger = logging.getLogger(__name__)

# Processed schema is identical to raw — posted_date stays VARCHAR so DuckDB
# load_comments_parquet can INSERT directly without type conversion.
PROCESSED_COMMENT_COLUMNS = RAW_COMMENT_COLUMNS

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(text: str | None) -> str | None:
    """Strip HTML tags and collapse whitespace. Returns None for blank results."""
    if not text:
        return None
    text = _HTML_TAG_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text or None


def process_docket(raw_parquet: Path, out_path: Path) -> pl.DataFrame:
    """Read raw comment Parquet, clean text fields, validate, and write processed output.

    Idempotent: always overwrites ``out_path``.
    Filters out rows whose ``comment_text`` is null or empty after cleaning
    (they carry no signal for NLP).
    """
    df = pl.read_parquet(raw_parquet)

    before = df.height
    df = df.with_columns(
        [
            pl.col("comment_text").map_elements(_clean_text, return_dtype=pl.String),
            pl.col("submitter_name").map_elements(_clean_text, return_dtype=pl.String),
        ]
    ).filter(pl.col("comment_text").is_not_null() & (pl.col("comment_text").str.len_chars() > 0))

    dropped = before - df.height
    if dropped:
        logger.info("dropped %d rows with empty comment_text after cleaning", dropped)

    validate(
        df,
        required=PROCESSED_COMMENT_COLUMNS,
        unique=("comment_id",),
        non_null=("comment_id", "docket_id", "fetched_at"),
        strict=True,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_path, compression="snappy")
    logger.info("processed %d comments → %s", df.height, out_path)
    return df
