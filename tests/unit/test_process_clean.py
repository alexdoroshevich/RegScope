"""Unit tests for data.process.clean."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path
import pytest

from data.process.clean import PROCESSED_COMMENT_COLUMNS, process_docket


def _make_raw(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    df = pl.DataFrame(rows, schema=PROCESSED_COMMENT_COLUMNS)
    p = tmp_path / "part-00000.parquet"
    df.write_parquet(p)
    return p


_NOW = datetime(2024, 1, 1, tzinfo=UTC)


def test_process_docket_basic(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": "2024-01-01",
                "submitter_name": "Alice",
                "comment_text": "Clean text.",
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "processed" / "comments.parquet"
    df = process_docket(raw, out)
    assert out.exists()
    assert df.height == 1
    assert df["comment_id"][0] == "c1"


def test_process_docket_strips_html(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "<p>Hello <b>world</b></p>",
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "out" / "comments.parquet"
    df = process_docket(raw, out)
    assert df["comment_text"][0] == "Hello world"


def test_process_docket_drops_empty_text(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "   ",
                "fetched_at": _NOW,
            },
            {
                "comment_id": "c2",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": None,
                "fetched_at": _NOW,
            },
            {
                "comment_id": "c3",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "Real comment.",
                "fetched_at": _NOW,
            },
        ],
    )
    out = tmp_path / "out" / "comments.parquet"
    df = process_docket(raw, out)
    assert df.height == 1
    assert df["comment_id"][0] == "c3"


def test_process_docket_normalises_whitespace(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "Too   many   spaces\n\nand newlines",
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "out" / "comments.parquet"
    df = process_docket(raw, out)
    assert df["comment_text"][0] == "Too many spaces and newlines"


def test_process_docket_idempotent(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "Hello.",
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "out" / "comments.parquet"
    df1 = process_docket(raw, out)
    df2 = process_docket(raw, out)
    assert df1.equals(df2)


def test_process_docket_creates_parent_dirs(tmp_path: Path) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": "Hi.",
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "deep" / "nested" / "comments.parquet"
    process_docket(raw, out)
    assert out.exists()


@pytest.mark.parametrize(
    "html,expected",
    [
        ("<b>bold</b>", "bold"),
        ("<p>para</p>", "para"),
        ("no tags", "no tags"),
        ("<br/>line", "line"),
    ],
)
def test_html_variants(tmp_path: Path, html: str, expected: str) -> None:
    raw = _make_raw(
        tmp_path,
        [
            {
                "comment_id": "c1",
                "docket_id": "D-001",
                "posted_date": None,
                "submitter_name": None,
                "comment_text": html,
                "fetched_at": _NOW,
            }
        ],
    )
    out = tmp_path / "out" / "comments.parquet"
    df = process_docket(raw, out)
    assert df["comment_text"][0] == expected
