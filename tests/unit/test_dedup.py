"""Tests for nlp.dedup — MinHash/LSH near-duplicate detection."""

from __future__ import annotations

import polars as pl
import pytest

from nlp.dedup import (
    DuplicateGroup,
    _normalize,
    _shingle,
    find_duplicate_groups,
    groups_to_dataframe,
)

TEMPLATE = "I strongly oppose this proposed rule and urge the agency to withdraw it immediately"


def _make_comments(
    identical: int = 5,
    unique: int = 5,
    *,
    same_submitter: bool = False,
) -> pl.DataFrame:
    """Build a DataFrame with ``identical`` copies + ``unique`` distinct comments."""
    rows: list[dict[str, str]] = []
    for i in range(identical):
        rows.append(
            {
                "comment_id": f"dup-{i}",
                "comment_text": TEMPLATE,
                "submitter_name": "Spammer" if same_submitter else f"Person {i}",
            }
        )
    diverse_texts = [
        "The environmental impact assessment fails to address water contamination risks",
        "Small businesses cannot absorb the compliance costs outlined in section three",
        "This regulation duplicates existing state level protections already in effect",
        "The proposed timeline is unrealistic given current supply chain constraints",
        "Consumer privacy protections in this draft are insufficient and need strengthening",
        "Agricultural stakeholders were not adequately consulted during the drafting phase",
        "The cost benefit analysis relies on outdated economic models from two decades ago",
        "Healthcare providers need at least eighteen months to implement these changes",
        "The cybersecurity requirements exceed what most mid size firms can reasonably achieve",
        "International trade implications of this rule have not been properly evaluated",
    ]
    for i in range(unique):
        rows.append(
            {
                "comment_id": f"uniq-{i}",
                "comment_text": diverse_texts[i % len(diverse_texts)],
                "submitter_name": f"Author {i}",
            }
        )
    return pl.DataFrame(rows)


class TestNormalize:
    def test_lowercases_and_strips_punctuation(self) -> None:
        assert _normalize("Hello, World!") == "hello world"

    def test_preserves_whitespace_between_words(self) -> None:
        assert _normalize("  two   words  ") == "two   words"

    def test_empty_string(self) -> None:
        assert _normalize("") == ""


class TestShingle:
    def test_short_text_returns_single_shingle(self) -> None:
        assert _shingle("hi") == {"hi"}

    def test_empty_text_returns_empty_set(self) -> None:
        assert _shingle("") == set()

    def test_known_shingle_count(self) -> None:
        shingles = _shingle("abcdef", k=5)
        assert shingles == {"abcde", "bcdef"}

    def test_punctuation_stripped_before_shingling(self) -> None:
        shingles_with = _shingle("a,b,c,d,e,f")
        shingles_without = _shingle("abcdef")
        assert shingles_with == shingles_without


class TestFindDuplicateGroups:
    def test_identical_comments_form_one_group(self) -> None:
        df = _make_comments(identical=5, unique=5)
        groups = find_duplicate_groups(df)
        assert len(groups) >= 1
        dup_ids = set()
        for g in groups:
            dup_ids.update(g.comment_ids)
        for i in range(5):
            assert f"dup-{i}" in dup_ids

    def test_unique_comments_not_grouped(self) -> None:
        df = _make_comments(identical=0, unique=10)
        groups = find_duplicate_groups(df)
        assert len(groups) == 0

    def test_campaign_likelihood_high_with_different_submitters(self) -> None:
        df = _make_comments(identical=10, unique=0, same_submitter=False)
        groups = find_duplicate_groups(df)
        assert len(groups) == 1
        assert groups[0].campaign_likelihood == 1.0
        assert groups[0].is_astroturf is False

    def test_campaign_likelihood_astroturf_with_same_submitter(self) -> None:
        df = _make_comments(identical=10, unique=0, same_submitter=True)
        groups = find_duplicate_groups(df)
        assert len(groups) == 1
        assert groups[0].unique_submitters == 1
        assert groups[0].campaign_likelihood == 10.0
        assert groups[0].is_astroturf is True

    def test_template_text_is_most_common_variant(self) -> None:
        rows = [
            {"comment_id": "a", "comment_text": TEMPLATE, "submitter_name": "A"},
            {"comment_id": "b", "comment_text": TEMPLATE, "submitter_name": "B"},
            {"comment_id": "c", "comment_text": TEMPLATE + " please", "submitter_name": "C"},
        ]
        df = pl.DataFrame(rows)
        groups = find_duplicate_groups(df)
        assert len(groups) == 1
        assert groups[0].template_text == TEMPLATE

    def test_empty_input_returns_empty_list(self) -> None:
        df = pl.DataFrame(
            {"comment_id": [], "comment_text": [], "submitter_name": []},
            schema={"comment_id": pl.Utf8, "comment_text": pl.Utf8, "submitter_name": pl.Utf8},
        )
        assert find_duplicate_groups(df) == []

    def test_null_text_comments_skipped(self) -> None:
        df = pl.DataFrame(
            {
                "comment_id": ["a", "b"],
                "comment_text": [None, None],
                "submitter_name": ["X", "Y"],
            }
        )
        assert find_duplicate_groups(df) == []

    def test_group_dataclass_is_frozen(self) -> None:
        g = DuplicateGroup(
            group_id=0,
            comment_ids=("a",),
            submitter_names=("X",),
            template_text="t",
            group_size=1,
            unique_submitters=1,
            campaign_likelihood=1.0,
            is_astroturf=False,
        )
        with pytest.raises(AttributeError):
            g.group_id = 99  # type: ignore[misc]


class TestGroupsToDataframe:
    def test_empty_groups_returns_correct_schema(self) -> None:
        df = groups_to_dataframe([])
        assert df.shape == (0, 7)
        assert "group_id" in df.columns
        assert "is_astroturf" in df.columns
        assert "template_text" in df.columns

    def test_round_trip_preserves_data(self) -> None:
        comments = _make_comments(identical=6, unique=0, same_submitter=True)
        groups = find_duplicate_groups(comments)
        df = groups_to_dataframe(groups)
        assert df.shape[0] == 1
        assert df["group_size"][0] == 6
        assert df["is_astroturf"][0] is True
        assert df["campaign_likelihood"][0] == 6.0
