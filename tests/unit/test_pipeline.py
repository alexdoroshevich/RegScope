"""Tests for the pipeline CLI — unit-level with all external calls mocked."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from scripts.pipeline import _dedup, _parse_args, main

if TYPE_CHECKING:
    from pathlib import Path


class TestParseArgs:
    def test_required_docket_id(self) -> None:
        args = _parse_args(["EPA-HQ-OAR-2021-0317"])
        assert args.docket_id == "EPA-HQ-OAR-2021-0317"
        assert args.skip_ingest is False
        assert args.skip_label is False
        assert args.min_cluster_size == 15

    def test_skip_flags(self) -> None:
        args = _parse_args(["DOC-1", "--skip-ingest", "--skip-label"])
        assert args.skip_ingest is True
        assert args.skip_label is True

    def test_min_cluster_size(self) -> None:
        args = _parse_args(["DOC-1", "--min-cluster-size", "25"])
        assert args.min_cluster_size == 25

    def test_missing_docket_id_exits(self) -> None:
        with pytest.raises(SystemExit):
            _parse_args([])


class TestDedup:
    def test_dedup_writes_parquet(self, tmp_path: Path) -> None:
        data_dir = tmp_path / "raw"
        pq_dir = data_dir / "comments" / "docket_id=DOC-1"
        pq_dir.mkdir(parents=True)
        df = pl.DataFrame(
            {
                "comment_id": ["C-1", "C-2", "C-3"],
                "comment_text": ["same text here", "same text here", "different text"],
                "submitter_name": ["A", "B", "C"],
                "docket_id": ["DOC-1"] * 3,
                "posted_date": ["2024-01-01"] * 3,
                "fetched_at": [None] * 3,
            }
        )
        df.write_parquet(pq_dir / "part-00000.parquet")

        out = _dedup(data_dir, "DOC-1")
        assert out.exists()
        result = pl.read_parquet(out)
        assert "group_id" in result.columns


class TestMainIntegration:
    @patch("scripts.pipeline._load_db")
    @patch("scripts.pipeline._label")
    @patch("scripts.pipeline._cluster")
    @patch("scripts.pipeline._embed")
    @patch("scripts.pipeline._dedup")
    def test_skip_ingest_skip_label(
        self,
        mock_dedup: MagicMock,
        mock_embed: MagicMock,
        mock_cluster: MagicMock,
        mock_label: MagicMock,
        mock_load: MagicMock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        data_dir = tmp_path / "raw"
        pq_dir = data_dir / "comments" / "docket_id=DOC-1"
        pq_dir.mkdir(parents=True)
        pl.DataFrame(
            {
                "comment_id": ["C-1"],
                "comment_text": ["hello"],
                "submitter_name": ["A"],
                "docket_id": ["DOC-1"],
                "posted_date": ["2024-01-01"],
                "fetched_at": [None],
            }
        ).write_parquet(pq_dir / "part-00000.parquet")

        monkeypatch.setenv("REGSCOPE_DATA_DIR", str(data_dir))
        monkeypatch.setenv("REGSCOPE_DB_PATH", str(tmp_path / "test.db"))

        main(["DOC-1", "--skip-ingest", "--skip-label"])

        mock_dedup.assert_called_once()
        mock_embed.assert_called_once()
        mock_cluster.assert_called_once()
        mock_label.assert_not_called()
        mock_load.assert_called_once()

    def test_skip_ingest_no_parquet_exits(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("REGSCOPE_DATA_DIR", str(tmp_path / "empty"))
        monkeypatch.setenv("REGSCOPE_DB_PATH", str(tmp_path / "test.db"))

        with pytest.raises(SystemExit):
            main(["DOC-1", "--skip-ingest"])
