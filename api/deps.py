"""FastAPI dependency providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.config import get_settings
from db.init_db import connect

if TYPE_CHECKING:
    from collections.abc import Generator

    import duckdb


def get_db() -> Generator[duckdb.DuckDBPyConnection]:
    """Yield a DuckDB connection scoped to the request."""
    settings = get_settings()
    conn = connect(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()
