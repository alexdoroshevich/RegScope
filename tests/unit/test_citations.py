"""Unit tests for nlp/citations.py."""

from __future__ import annotations

import polars as pl
import pytest

from nlp.citations import Citation, extract_citations, extract_citations_from_df


class TestExtractCitations:
    def test_cfr_part_basic(self) -> None:
        results = extract_citations("C-001", "DOC-1", "See 40 CFR Part 60 for limits.")
        assert any(
            c.citation_type == "CFR" and c.cfr_title == 40 and c.cfr_part == 60 for c in results
        )

    def test_cfr_with_dots(self) -> None:
        results = extract_citations("C-001", "DOC-1", "Per 40 C.F.R. 63, emissions are controlled.")
        assert any(c.cfr_title == 40 and c.cfr_part == 63 for c in results)

    def test_cfr_section(self) -> None:
        results = extract_citations("C-001", "DOC-1", "Refer to 40 CFR § 60.5.")
        assert any(c.cfr_title == 40 and c.cfr_part == 60 for c in results)

    def test_usc_basic(self) -> None:
        results = extract_citations("C-001", "DOC-1", "Under 5 U.S.C. § 553, notice is required.")
        assert any(
            c.citation_type == "USC" and c.cfr_title == 5 and c.cfr_part == 553 for c in results
        )

    def test_usc_without_dots(self) -> None:
        results = extract_citations("C-001", "DOC-1", "5 USC 706 limits agency action.")
        assert any(c.citation_type == "USC" and c.cfr_part == 706 for c in results)

    def test_multiple_citations(self) -> None:
        text = "See 40 CFR Part 60 and 5 U.S.C. § 553 and 40 CFR Part 98."
        results = extract_citations("C-001", "DOC-1", text)
        types = {(c.cfr_title, c.cfr_part) for c in results}
        assert (40, 60) in types
        assert (40, 98) in types
        assert (5, 553) in types

    def test_deduplication_within_comment(self) -> None:
        text = "40 CFR Part 60 is cited here. Also see 40 CFR Part 60 again."
        results = extract_citations("C-001", "DOC-1", text)
        cfr_60 = [c for c in results if c.cfr_title == 40 and c.cfr_part == 60]
        assert len(cfr_60) == 1

    def test_empty_text_returns_empty(self) -> None:
        assert extract_citations("C-001", "DOC-1", "") == []

    def test_no_citations_returns_empty(self) -> None:
        assert extract_citations("C-001", "DOC-1", "This comment has no citations at all.") == []

    def test_comment_id_preserved(self) -> None:
        results = extract_citations("MY-ID", "MY-DOCKET", "See 40 CFR Part 60.")
        assert all(c.comment_id == "MY-ID" for c in results)
        assert all(c.docket_id == "MY-DOCKET" for c in results)

    def test_returns_citation_dataclass(self) -> None:
        results = extract_citations("C-001", "DOC-1", "See 40 CFR Part 60.")
        assert all(isinstance(c, Citation) for c in results)


class TestExtractCitationsFromDf:
    def _make_df(self, rows: list[dict[str, str]]) -> pl.DataFrame:
        return pl.DataFrame(rows)

    def test_basic(self) -> None:
        df = self._make_df(
            [
                {"comment_id": "C-001", "docket_id": "D-1", "comment_text": "See 40 CFR Part 60."},
                {"comment_id": "C-002", "docket_id": "D-1", "comment_text": "No citations here."},
            ]
        )
        out = extract_citations_from_df(df)
        assert out.height == 1
        assert out["cfr_title"][0] == 40

    def test_empty_df_returns_schema(self) -> None:
        df = pl.DataFrame(
            {"comment_id": [], "docket_id": [], "comment_text": []},
            schema={"comment_id": pl.String, "docket_id": pl.String, "comment_text": pl.String},
        )
        out = extract_citations_from_df(df)
        assert out.height == 0
        assert "citation_text" in out.columns

    def test_no_citations_returns_empty(self) -> None:
        df = self._make_df(
            [
                {"comment_id": "C-001", "docket_id": "D-1", "comment_text": "Plain comment."},
            ]
        )
        out = extract_citations_from_df(df)
        assert out.height == 0

    def test_missing_column_raises(self) -> None:
        df = pl.DataFrame({"comment_id": ["C-001"], "comment_text": ["See 40 CFR Part 60."]})
        with pytest.raises(ValueError, match="missing columns"):
            extract_citations_from_df(df)

    def test_output_schema(self) -> None:
        df = self._make_df(
            [
                {"comment_id": "C-001", "docket_id": "D-1", "comment_text": "See 40 CFR Part 60."},
            ]
        )
        out = extract_citations_from_df(df)
        expected = {
            "comment_id",
            "docket_id",
            "citation_text",
            "citation_type",
            "cfr_title",
            "cfr_part",
        }
        assert set(out.columns) == expected
