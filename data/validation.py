"""Polars-native schema validation at pipeline boundaries.

Replaces :mod:`pandera` for the simple schemas RegScope needs (presence,
dtype, nullability, uniqueness). Avoids pulling pandas as a transitive
dependency. See ``docs/DECISIONS.md`` (ADR-0001).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


class SchemaValidationError(ValueError):
    """Raised when a Polars DataFrame fails schema validation."""


def validate(
    frame: pl.DataFrame,
    *,
    required: dict[str, pl.DataType],
    unique: tuple[str, ...] = (),
    non_null: tuple[str, ...] = (),
    strict: bool = True,
) -> None:
    """Validate ``frame`` against a minimal schema spec.

    Checks run in order and raise on the first failure:

    1. every column in ``required`` is present;
    2. each column's dtype equals its spec;
    3. if ``strict`` is ``True``, there are no columns outside ``required``;
    4. every column in ``non_null`` has zero null rows;
    5. every column in ``unique`` has no duplicate values.
    """
    actual = dict(frame.schema)

    missing = [name for name in required if name not in actual]
    if missing:
        raise SchemaValidationError(f"missing required columns: {missing}")

    for name, want in required.items():
        got = actual[name]
        if got != want:
            raise SchemaValidationError(f"column {name!r}: expected dtype {want!r}, got {got!r}")

    if strict:
        extra = [name for name in actual if name not in required]
        if extra:
            raise SchemaValidationError(f"unexpected columns: {extra}")

    for name in non_null:
        nulls = frame[name].null_count()
        if nulls:
            raise SchemaValidationError(f"column {name!r} has {nulls} null row(s)")

    for name in unique:
        dup_mask = frame[name].is_duplicated()
        if bool(dup_mask.any()):
            dupes = frame.filter(dup_mask)[name].unique().to_list()[:5]
            raise SchemaValidationError(f"column {name!r} has duplicate values (sample): {dupes}")
