"""Citation extraction from regulatory comments using spaCy + regex.

Uses spaCy's sentence segmenter to split text into sentences, then applies
regex patterns to detect CFR (Code of Federal Regulations) and USC
(United States Code) citations within each sentence.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    import spacy.language

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches "40 CFR Part 60", "40 CFR § 60.5", "40 C.F.R. 60"
_CFR_RE = re.compile(
    r"\b(\d{1,2})\s+C\.?F\.?R\.?\s*(?:(?:Part|§|Sec\.?|Section)\s*)?(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)

# Matches "5 U.S.C. § 553", "5 USC 553"
_USC_RE = re.compile(
    r"\b(\d{1,2})\s+U\.?S\.?C\.?\s*§?\s*(\d+(?:\.\d+)?)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Citation:
    """A single regulatory citation extracted from a comment."""

    comment_id: str
    docket_id: str
    citation_text: str
    citation_type: str  # 'CFR' or 'USC'
    cfr_title: int | None = None
    cfr_part: int | None = None


# ---------------------------------------------------------------------------
# spaCy model (lazy-loaded, shared)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _get_nlp() -> spacy.language.Language:
    """Load spaCy model once; keep only the sentencizer for efficiency."""
    import spacy

    nlp = spacy.load("en_core_web_sm", disable=["tagger", "ner", "lemmatizer", "attribute_ruler"])
    return nlp


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_from_sentence(
    sent: str,
    comment_id: str,
    docket_id: str,
) -> list[Citation]:
    """Return all CFR and USC citations found in a single sentence."""
    results: list[Citation] = []

    for m in _CFR_RE.finditer(sent):
        results.append(
            Citation(
                comment_id=comment_id,
                docket_id=docket_id,
                citation_text=m.group(0).strip(),
                citation_type="CFR",
                cfr_title=int(m.group(1)),
                cfr_part=int(float(m.group(2))),
            )
        )

    for m in _USC_RE.finditer(sent):
        results.append(
            Citation(
                comment_id=comment_id,
                docket_id=docket_id,
                citation_text=m.group(0).strip(),
                citation_type="USC",
                cfr_title=int(m.group(1)),
                cfr_part=int(float(m.group(2))),
            )
        )

    return results


def extract_citations(comment_id: str, docket_id: str, text: str) -> list[Citation]:
    """Extract all citations from a single comment.

    Uses spaCy sentence segmentation so that citations are never matched
    across sentence boundaries.
    """
    if not text or not text.strip():
        return []

    nlp = _get_nlp()
    doc = nlp(text)
    citations: list[Citation] = []
    seen: set[str] = set()

    for sent in doc.sents:
        for c in _extract_from_sentence(sent.text, comment_id, docket_id):
            key = f"{c.citation_type}:{c.cfr_title}:{c.cfr_part}"
            if key not in seen:
                seen.add(key)
                citations.append(c)

    return citations


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------


def extract_citations_from_df(df: pl.DataFrame) -> pl.DataFrame:
    """Extract citations from all comments in a Polars DataFrame.

    Args:
        df: Must have columns ``comment_id``, ``docket_id``, ``comment_text``.

    Returns:
        DataFrame with columns matching the ``citations`` DB table schema.
    """
    required = {"comment_id", "docket_id", "comment_text"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing columns: {missing}")

    rows: list[Citation] = []
    for row in df.iter_rows(named=True):
        cid: str = row["comment_id"]
        did: str = row["docket_id"]
        text: str = row["comment_text"] or ""
        rows.extend(extract_citations(cid, did, text))

    logger.info("extracted %d citations from %d comments", len(rows), df.height)

    if not rows:
        return pl.DataFrame(
            schema={
                "comment_id": pl.String,
                "docket_id": pl.String,
                "citation_text": pl.String,
                "citation_type": pl.String,
                "cfr_title": pl.Int32,
                "cfr_part": pl.Int32,
            }
        )

    return pl.DataFrame(
        {
            "comment_id": [r.comment_id for r in rows],
            "docket_id": [r.docket_id for r in rows],
            "citation_text": [r.citation_text for r in rows],
            "citation_type": [r.citation_type for r in rows],
            "cfr_title": [r.cfr_title for r in rows],
            "cfr_part": [r.cfr_part for r in rows],
        },
        schema={
            "comment_id": pl.String,
            "docket_id": pl.String,
            "citation_text": pl.String,
            "citation_type": pl.String,
            "cfr_title": pl.Int32,
            "cfr_part": pl.Int32,
        },
    )
