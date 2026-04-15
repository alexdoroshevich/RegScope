"""Unit tests for api.config.Settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from api.config import Settings, get_settings

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_settings_reads_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("REGULATIONS_GOV_API_KEY", "test-key")
    monkeypatch.setenv("REGSCOPE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("REGSCOPE_LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.regulations_gov_api_key == "test-key"
    assert settings.data_dir == tmp_path
    assert settings.log_level == "DEBUG"


def test_get_settings_is_cached() -> None:
    first = get_settings()
    second = get_settings()
    assert first is second
