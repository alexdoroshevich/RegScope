"""Shared pytest fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    """Ephemeral FEDCOMMENT_DATA_DIR for tests — cleaned up automatically."""
    path = tmp_path / "raw"
    path.mkdir()
    return path


@pytest.fixture
def sample_comment_payload() -> dict[str, Any]:
    """A minimal Regulations.gov /v4/comments payload with two rows."""
    return {
        "data": [
            {
                "id": "EPA-HQ-OAR-2021-0317-0001",
                "type": "comments",
                "attributes": {
                    "postedDate": "2024-03-01T12:00:00Z",
                    "submitterName": "Jane Public",
                    "comment": "Please strengthen the rule.",
                },
            },
            {
                "id": "EPA-HQ-OAR-2021-0317-0002",
                "type": "comments",
                "attributes": {
                    "postedDate": "2024-03-02T09:15:00Z",
                    "submitterName": "John Public",
                    "comment": "I oppose this rule.",
                },
            },
        ],
        "meta": {"totalElements": 2, "pageSize": 250, "pageNumber": 1},
    }


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> Iterator[None]:
    """Clear the Settings lru_cache between tests so env monkeypatches take effect."""
    from api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
