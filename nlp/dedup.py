"""MinHash/LSH near-duplicate detection for astroturf campaign scoring."""

from __future__ import annotations

import contextlib
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING

from datasketch import MinHash, MinHashLSH

if TYPE_CHECKING:
    import polars as pl

logger = logging.getLogger(__name__)

NUM_PERM = 128
LSH_THRESHOLD = 0.8
ASTROTURF_THRESHOLD = 5.0
SHINGLE_K = 5

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def _normalize(text: str) -> str:
    """Lowercase, strip whitespace, remove punctuation."""
    return _PUNCT_RE.sub("", text.lower()).strip()


def _shingle(text: str, k: int = SHINGLE_K) -> set[str]:
    """Create character-level k-shingles from normalized text."""
    normed = _normalize(text)
    if len(normed) < k:
        return {normed} if normed else set()
    return {normed[i : i + k] for i in range(len(normed) - k + 1)}


def _build_minhash(shingles: set[str], num_perm: int = NUM_PERM) -> MinHash:
    """Build a MinHash signature from a set of shingles."""
    mh = MinHash(num_perm=num_perm)
    for s in shingles:
        mh.update(s.encode("utf-8"))
    return mh


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """A group of near-duplicate comments with campaign scoring."""

    group_id: int
    comment_ids: tuple[str, ...]
    submitter_names: tuple[str, ...]
    template_text: str
    group_size: int
    unique_submitters: int
    campaign_likelihood: float
    is_astroturf: bool


def find_duplicate_groups(
    comments: pl.DataFrame,
    *,
    num_perm: int = NUM_PERM,
    threshold: float = LSH_THRESHOLD,
    astroturf_threshold: float = ASTROTURF_THRESHOLD,
) -> list[DuplicateGroup]:
    """Find near-duplicate comment groups using MinHash/LSH.

    Expects columns: ``comment_id``, ``comment_text``, ``submitter_name``.
    """
    minhashes: dict[str, MinHash] = {}
    texts: dict[str, str] = {}
    submitters: dict[str, str] = {}

    for row in comments.iter_rows(named=True):
        comment_id: str = row["comment_id"]
        text: str = row["comment_text"] or ""
        submitter: str = row["submitter_name"] or "Anonymous"

        shingles = _shingle(text)
        if not shingles:
            continue

        minhashes[comment_id] = _build_minhash(shingles, num_perm)
        texts[comment_id] = text
        submitters[comment_id] = submitter

    if not minhashes:
        return []

    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    for cid, mh in minhashes.items():
        with contextlib.suppress(ValueError):
            lsh.insert(cid, mh)

    visited: set[str] = set()
    raw_groups: list[set[str]] = []

    for cid, mh in minhashes.items():
        if cid in visited:
            continue
        neighbors = set(lsh.query(mh))
        if len(neighbors) < 2:
            continue
        component: set[str] = set()
        frontier = list(neighbors)
        while frontier:
            node = frontier.pop()
            if node in component:
                continue
            component.add(node)
            for nn in lsh.query(minhashes[node]):
                if nn not in component:
                    frontier.append(nn)
        visited |= component
        raw_groups.append(component)

    groups: list[DuplicateGroup] = []
    for gid, component in enumerate(raw_groups):
        cids = tuple(sorted(component))
        subs = tuple(submitters.get(c, "Anonymous") for c in cids)
        group_texts = [texts[c] for c in cids]

        template = Counter(group_texts).most_common(1)[0][0]

        size = len(cids)
        unique = len(set(subs))
        likelihood = size / max(unique, 1)

        groups.append(
            DuplicateGroup(
                group_id=gid,
                comment_ids=cids,
                submitter_names=subs,
                template_text=template,
                group_size=size,
                unique_submitters=unique,
                campaign_likelihood=likelihood,
                is_astroturf=likelihood > astroturf_threshold,
            )
        )

    logger.info(
        "found %d duplicate groups (%d astroturf) from %d comments",
        len(groups),
        sum(1 for g in groups if g.is_astroturf),
        len(minhashes),
    )
    return groups


def groups_to_dataframe(groups: list[DuplicateGroup]) -> pl.DataFrame:
    """Convert duplicate groups to a Polars DataFrame for Parquet storage."""
    import polars as pl

    if not groups:
        return pl.DataFrame(
            schema={
                "group_id": pl.Int64,
                "comment_ids": pl.List(pl.Utf8),
                "group_size": pl.Int64,
                "unique_submitters": pl.Int64,
                "campaign_likelihood": pl.Float64,
                "is_astroturf": pl.Boolean,
                "template_text": pl.Utf8,
            }
        )

    return pl.DataFrame(
        {
            "group_id": [g.group_id for g in groups],
            "comment_ids": [list(g.comment_ids) for g in groups],
            "group_size": [g.group_size for g in groups],
            "unique_submitters": [g.unique_submitters for g in groups],
            "campaign_likelihood": [g.campaign_likelihood for g in groups],
            "is_astroturf": [g.is_astroturf for g in groups],
            "template_text": [g.template_text for g in groups],
        }
    )
