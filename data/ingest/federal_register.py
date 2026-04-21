"""Async client and CLI for the Federal Register public API.

Fetches regulatory documents (Rules, Proposed Rules, Notices) for a
date range and writes them to Parquet, partitioned by publication year.
No API key is required.  Rate-limited to ~1 req/sec as per Federal
Register guidance.

CLI usage::

    uv run python -m data.ingest.federal_register --since 2023-01-01
    uv run python -m data.ingest.federal_register --since 2023-01-01 --until 2023-12-31
    uv run python -m data.ingest.federal_register --since 2024-01-01 --types RULE PRORULE
    uv run python -m data.ingest.federal_register --since 2024-01-01 --agency epa
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
import shutil
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import polars as pl

from data.validation import validate

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path
    from types import TracebackType

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://www.federalregister.gov/api/v1"
DEFAULT_PAGE_SIZE = 1000  # FR API maximum per_page
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MIN_INTERVAL_S = 1.0  # ~1 req/sec; Federal Register guidance
MAX_RETRIES = 3
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

# Fields to request from the API — only what we store.
_FIELDS = (
    "document_number",
    "title",
    "type",
    "abstract",
    "agency_names",
    "publication_date",
    "effective_on",
    "comments_close_on",
    "html_url",
    "citation",
    "significant",
    "docket_ids",
)

DOCUMENT_COLUMNS: dict[str, pl.DataType] = {
    "document_number": pl.String(),
    "docket_id": pl.String(),  # first entry of docket_ids, or null
    "title": pl.String(),
    "doc_type": pl.String(),  # RULE | PRORULE | NOTICE | …
    "abstract": pl.String(),
    "agency_names": pl.String(),  # JSON-encoded list
    "publication_date": pl.String(),
    "effective_on": pl.String(),
    "comments_close_on": pl.String(),
    "html_url": pl.String(),
    "citation": pl.String(),
    "significant": pl.Boolean(),
    "fetched_at": pl.Datetime(time_unit="us", time_zone="UTC"),
}


def validate_documents(frame: pl.DataFrame) -> None:
    """Validate a documents DataFrame before writing to Parquet."""
    validate(
        frame,
        required=DOCUMENT_COLUMNS,
        unique=("document_number",),
        non_null=("document_number", "fetched_at"),
        strict=True,
    )


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    """A single Federal Register document row ready for Parquet ingest."""

    document_number: str
    docket_id: str | None
    title: str
    doc_type: str
    abstract: str | None
    agency_names: str  # JSON list, e.g. '["EPA", "OSHA"]'
    publication_date: str | None
    effective_on: str | None
    comments_close_on: str | None
    html_url: str | None
    citation: str | None
    significant: bool | None


class FederalRegisterError(RuntimeError):
    """Raised when the Federal Register API returns a non-retryable error."""


class FederalRegisterClient:
    """Async client for the Federal Register documents API.

    No API key is required.  Applies a minimum-interval throttle and
    retries transient failures with exponential backoff.

    Usage::

        async with FederalRegisterClient() as client:
            async for doc in client.iter_documents(since="2024-01-01"):
                ...
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        min_request_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        max_retries: int = MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._min_interval_s = min_request_interval_s
        self._max_retries = max_retries
        self._last_request_monotonic: float = 0.0
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            headers={"Accept": "application/json"},
            timeout=httpx.Timeout(timeout_s),
            transport=transport,
        )

    async def __aenter__(self) -> FederalRegisterClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def iter_documents(
        self,
        *,
        since: str,
        until: str | None = None,
        doc_types: tuple[str, ...] = ("RULE", "PRORULE", "NOTICE"),
        agency: str | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> AsyncIterator[NormalizedDocument]:
        """Yield every document matching the given filters.

        Args:
            since: Earliest publication date, inclusive (``YYYY-MM-DD``).
            until: Latest publication date, inclusive (``YYYY-MM-DD``).
                   Defaults to today.
            doc_types: Document types to include.
            agency: Optional agency slug (e.g. ``"epa"``, ``"fcc"``).
            page_size: Results per API request (max 1000).
        """
        page = 1
        while True:
            params: dict[str, Any] = {
                "conditions[publication_date][gte]": since,
                "per_page": page_size,
                "page": page,
                "order": "oldest",
            }
            if until:
                params["conditions[publication_date][lte]"] = until
            for t in doc_types:
                params.setdefault("conditions[type][]", [])
                if isinstance(params["conditions[type][]"], list):
                    params["conditions[type][]"].append(t)
            if agency:
                params["conditions[agency_ids][]"] = agency
            for field in _FIELDS:
                params.setdefault("fields[]", [])
                if isinstance(params["fields[]"], list):
                    params["fields[]"].append(field)

            payload = await self._get_with_retry("/documents.json", params)
            results: list[dict[str, Any]] = payload.get("results") or []
            total_pages: int = payload.get("total_pages") or 1

            logger.info(
                "federal-register fetched since=%s page=%d/%d rows=%d",
                since,
                page,
                total_pages,
                len(results),
            )

            for row in results:
                yield _normalize(row)

            if page >= total_pages or not results:
                return
            page += 1

    async def _get_with_retry(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._max_retries):
            await self._throttle()
            try:
                response = await self._client.get(url, params=params)
            except httpx.HTTPError as err:
                last_exc = err
                await self._sleep_backoff(attempt)
                continue

            if response.status_code in RETRYABLE_STATUSES:
                logger.warning(
                    "federal-register retryable status=%d attempt=%d path=%s",
                    response.status_code,
                    attempt + 1,
                    path,
                )
                await self._sleep_backoff(attempt)
                continue

            if response.status_code >= 400:
                raise FederalRegisterError(
                    f"GET {path} returned {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            if not isinstance(data, dict):
                raise FederalRegisterError(f"GET {path} returned non-object body")
            return data

        raise FederalRegisterError(
            f"GET {path} failed after {self._max_retries} attempts"
        ) from last_exc

    async def _throttle(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._min_interval_s - (now - self._last_request_monotonic)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_monotonic = time.monotonic()

    @staticmethod
    async def _sleep_backoff(attempt: int) -> None:
        """Exponential backoff with jitter: 1s, 2s, 4s (+/- 25%)."""
        base = 2**attempt
        jitter = base * 0.25 * (2 * random.random() - 1)
        await asyncio.sleep(max(0.1, base + jitter))


def _normalize(row: dict[str, Any]) -> NormalizedDocument:
    """Convert a raw Federal Register API result dict to a NormalizedDocument."""
    docket_ids: list[str] = row.get("docket_ids") or []
    agency_names: list[str] = row.get("agency_names") or []
    return NormalizedDocument(
        document_number=str(row.get("document_number") or ""),
        docket_id=docket_ids[0] if docket_ids else None,
        title=str(row.get("title") or ""),
        doc_type=str(row.get("type") or ""),
        abstract=_str_or_none(row.get("abstract")),
        agency_names=json.dumps(agency_names),
        publication_date=_str_or_none(row.get("publication_date")),
        effective_on=_str_or_none(row.get("effective_on")),
        comments_close_on=_str_or_none(row.get("comments_close_on")),
        html_url=_str_or_none(row.get("html_url")),
        citation=_str_or_none(row.get("citation")),
        significant=row.get("significant"),
    )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def write_documents_parquet(
    documents: list[NormalizedDocument],
    *,
    data_dir: Path,
    fetched_at: datetime | None = None,
) -> dict[int, Path]:
    """Write ``documents`` to Parquet, partitioned by publication year.

    Returns a mapping of ``{year: path}`` for every partition written.
    Existing partitions for the same year are replaced atomically.
    """
    stamp = fetched_at or datetime.now(UTC)

    # Group by publication year (docs with no date go to year 0).
    by_year: dict[int, list[NormalizedDocument]] = {}
    for doc in documents:
        year = 0
        if doc.publication_date:
            with contextlib.suppress(ValueError):
                year = int(doc.publication_date[:4])
        by_year.setdefault(year, []).append(doc)

    written: dict[int, Path] = {}
    for year, docs in sorted(by_year.items()):
        rows = [
            {
                "document_number": d.document_number,
                "docket_id": d.docket_id,
                "title": d.title,
                "doc_type": d.doc_type,
                "abstract": d.abstract,
                "agency_names": d.agency_names,
                "publication_date": d.publication_date,
                "effective_on": d.effective_on,
                "comments_close_on": d.comments_close_on,
                "html_url": d.html_url,
                "citation": d.citation,
                "significant": d.significant,
                "fetched_at": stamp,
            }
            for d in docs
        ]
        frame = pl.DataFrame(rows, schema=DOCUMENT_COLUMNS)
        validate_documents(frame)

        partition_dir = data_dir / "documents" / f"year={year}"
        if partition_dir.exists():
            shutil.rmtree(partition_dir)
        partition_dir.mkdir(parents=True, exist_ok=True)

        out_path = partition_dir / "part-00000.parquet"
        frame.write_parquet(out_path, compression="snappy")
        logger.info("wrote %d documents (year=%d) → %s", frame.height, year, out_path)
        written[year] = out_path

    return written


async def _run(
    since: str,
    until: str | None,
    doc_types: tuple[str, ...],
    agency: str | None,
    data_dir: Path,
) -> None:
    """Fetch documents and write to Parquet."""
    from api.config import get_settings

    settings = get_settings()
    effective_data_dir = data_dir or settings.data_dir

    docs: list[NormalizedDocument] = []
    async with FederalRegisterClient() as client:
        async for doc in client.iter_documents(
            since=since,
            until=until,
            doc_types=doc_types,
            agency=agency,
        ):
            docs.append(doc)

    if not docs:
        logger.info("federal-register: no documents found for given filters")
        return

    written = write_documents_parquet(docs, data_dir=effective_data_dir)
    total = sum(pl.read_parquet(p).height for p in written.values())
    logger.info(
        "federal-register: %d documents written across %d year partition(s)",
        total,
        len(written),
    )


def _main() -> None:
    import argparse
    from pathlib import Path

    from api.logging_setup import configure_logging

    configure_logging()

    parser = argparse.ArgumentParser(description="Ingest Federal Register documents to Parquet.")
    parser.add_argument(
        "--since",
        required=True,
        metavar="YYYY-MM-DD",
        help="Earliest publication date (inclusive).",
    )
    parser.add_argument(
        "--until",
        default=None,
        metavar="YYYY-MM-DD",
        help="Latest publication date (inclusive). Defaults to today.",
    )
    parser.add_argument(
        "--types",
        nargs="+",
        default=["RULE", "PRORULE", "NOTICE"],
        metavar="TYPE",
        help="Document types to fetch (default: RULE PRORULE NOTICE).",
    )
    parser.add_argument(
        "--agency",
        default=None,
        metavar="SLUG",
        help="Agency slug filter, e.g. 'epa' or 'fcc'.",
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        type=Path,
        metavar="DIR",
        help="Override data directory (default: FEDCOMMENT_DATA_DIR from .env).",
    )

    args = parser.parse_args()
    asyncio.run(
        _run(
            since=args.since,
            until=args.until,
            doc_types=tuple(t.upper() for t in args.types),
            agency=args.agency,
            data_dir=args.data_dir,
        )
    )


if __name__ == "__main__":
    _main()
