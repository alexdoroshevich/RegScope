"""Unit tests for data.ingest.writer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl
import pytest

from data.ingest.regulations_gov import NormalizedComment
from data.ingest.writer import write_comments_parquet

if TYPE_CHECKING:
    from pathlib import Path


def _comment(i: int) -> NormalizedComment:
    return NormalizedComment(
        comment_id=f"C-{i:03d}",
        docket_id="D-1",
        posted_date="2024-03-01T12:00:00Z",
        submitter_name=f"Submitter {i}",
        comment_text=f"body {i}",
    )


def test_write_parquet_round_trip(data_dir: Path) -> None:
    stamp = datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)
    out = write_comments_parquet(
        [_comment(1), _comment(2)],
        data_dir=data_dir,
        docket_id="D-1",
        fetched_at=stamp,
    )

    assert out.exists()
    assert out.parent.name == "docket_id=D-1"

    frame = pl.read_parquet(out)
    assert frame.height == 2
    assert set(frame.columns) == {
        "comment_id",
        "docket_id",
        "posted_date",
        "submitter_name",
        "comment_text",
        "fetched_at",
    }
    assert frame["fetched_at"][0] == stamp


def test_write_parquet_is_idempotent(data_dir: Path) -> None:
    write_comments_parquet([_comment(1), _comment(2)], data_dir=data_dir, docket_id="D-1")
    out = write_comments_parquet([_comment(3)], data_dir=data_dir, docket_id="D-1")
    frame = pl.read_parquet(out)
    assert frame.height == 1
    assert frame["comment_id"][0] == "C-003"


def test_write_parquet_empty_input_writes_empty_file(data_dir: Path) -> None:
    out = write_comments_parquet([], data_dir=data_dir, docket_id="D-1")
    frame = pl.read_parquet(out)
    assert frame.height == 0
    assert set(frame.columns) == {
        "comment_id",
        "docket_id",
        "posted_date",
        "submitter_name",
        "comment_text",
        "fetched_at",
    }


def test_write_parquet_rejects_empty_docket(data_dir: Path) -> None:
    with pytest.raises(ValueError):
        write_comments_parquet([], data_dir=data_dir, docket_id="")


def test_write_parquet_rejects_duplicate_ids(data_dir: Path) -> None:
    from data.validation import SchemaValidationError

    with pytest.raises(SchemaValidationError):
        write_comments_parquet([_comment(1), _comment(1)], data_dir=data_dir, docket_id="D-1")
