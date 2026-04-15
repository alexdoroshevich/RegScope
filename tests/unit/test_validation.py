"""Unit tests for data.validation."""

from __future__ import annotations

import polars as pl
import pytest

from data.validation import SchemaValidationError, validate


def _schema() -> dict[str, pl.DataType]:
    return {"id": pl.String(), "n": pl.Int64()}


def test_validate_passes_on_clean_frame() -> None:
    frame = pl.DataFrame({"id": ["a", "b"], "n": [1, 2]}, schema=_schema())
    validate(frame, required=_schema(), unique=("id",), non_null=("id", "n"))


def test_validate_rejects_missing_column() -> None:
    frame = pl.DataFrame({"id": ["a"]}, schema={"id": pl.String()})
    with pytest.raises(SchemaValidationError, match="missing required columns"):
        validate(frame, required=_schema())


def test_validate_rejects_wrong_dtype() -> None:
    frame = pl.DataFrame({"id": ["a"], "n": ["1"]}, schema={"id": pl.String(), "n": pl.String()})
    with pytest.raises(SchemaValidationError, match="expected dtype"):
        validate(frame, required=_schema())


def test_validate_rejects_extra_column_in_strict_mode() -> None:
    frame = pl.DataFrame(
        {"id": ["a"], "n": [1], "extra": [9]},
        schema={"id": pl.String(), "n": pl.Int64(), "extra": pl.Int64()},
    )
    with pytest.raises(SchemaValidationError, match="unexpected columns"):
        validate(frame, required=_schema(), strict=True)


def test_validate_allows_extra_column_when_not_strict() -> None:
    frame = pl.DataFrame(
        {"id": ["a"], "n": [1], "extra": [9]},
        schema={"id": pl.String(), "n": pl.Int64(), "extra": pl.Int64()},
    )
    validate(frame, required=_schema(), strict=False)


def test_validate_rejects_null_in_non_null_column() -> None:
    frame = pl.DataFrame({"id": ["a", None], "n": [1, 2]}, schema=_schema())
    with pytest.raises(SchemaValidationError, match="null row"):
        validate(frame, required=_schema(), non_null=("id",))


def test_validate_rejects_duplicates() -> None:
    frame = pl.DataFrame({"id": ["a", "a"], "n": [1, 2]}, schema=_schema())
    with pytest.raises(SchemaValidationError, match="duplicate values"):
        validate(frame, required=_schema(), unique=("id",))
