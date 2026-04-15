"""Async client for the Regulations.gov v4 public API.

Fetches public comments for a docket. Respects the documented 1000 req/hr
per-key rate limit via a minimum-interval throttle, retries 429/5xx with
exponential backoff, and normalizes response payloads into plain dicts.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import TracebackType

logger = logging.getLogger(__name__)

BASE_URL = "https://api.regulations.gov/v4"
DEFAULT_PAGE_SIZE = 250
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MIN_INTERVAL_S = 3.6
MAX_RETRIES = 3
RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class NormalizedComment:
    """A single comment row, already normalized for Parquet ingest."""

    comment_id: str
    docket_id: str
    posted_date: str | None
    submitter_name: str | None
    comment_text: str | None


class RegulationsGovError(RuntimeError):
    """Raised when the Regulations.gov API returns a non-retryable error."""


class RegulationsGovClient:
    """Async client for a single Regulations.gov API key.

    Usage:

        async with RegulationsGovClient(api_key) as client:
            async for comment in client.iter_comments("EPA-HQ-OAR-2021-0317"):
                ...
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        min_request_interval_s: float = DEFAULT_MIN_INTERVAL_S,
        max_retries: int = MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self._base_url = base_url.rstrip("/")
        self._min_interval_s = min_request_interval_s
        self._max_retries = max_retries
        self._last_request_monotonic: float = 0.0
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            headers={"X-Api-Key": api_key, "Accept": "application/json"},
            timeout=httpx.Timeout(timeout_s),
            transport=transport,
        )

    async def __aenter__(self) -> RegulationsGovClient:
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

    async def iter_comments(
        self,
        docket_id: str,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> AsyncIterator[NormalizedComment]:
        """Yield every comment on ``docket_id`` across all pages.

        Pagination continues until the API returns an empty page or a page
        shorter than ``page_size``.
        """
        page = 1
        while True:
            params: dict[str, Any] = {
                "filter[docketId]": docket_id,
                "page[number]": page,
                "page[size]": page_size,
                "sort": "postedDate",
            }
            payload = await self._get_with_retry("/comments", params)
            rows = payload.get("data") or []
            logger.info(
                "regulations.gov fetched docket=%s page=%d rows=%d",
                docket_id,
                page,
                len(rows),
            )
            for row in rows:
                yield _normalize(row, docket_id)
            if len(rows) < page_size:
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
                    "regulations.gov retryable status=%d attempt=%d path=%s",
                    response.status_code,
                    attempt + 1,
                    path,
                )
                await self._sleep_backoff(attempt)
                continue

            if response.status_code >= 400:
                raise RegulationsGovError(
                    f"GET {path} returned {response.status_code}: {response.text[:200]}"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise RegulationsGovError(f"GET {path} returned non-object body")
            return data

        raise RegulationsGovError(
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
        # Exponential backoff with jitter: 1s, 2s, 4s (+/- 25%).
        base = 2**attempt
        jitter = base * 0.25 * (2 * random.random() - 1)
        await asyncio.sleep(max(0.1, base + jitter))


def _normalize(row: dict[str, Any], docket_id: str) -> NormalizedComment:
    attrs = row.get("attributes") or {}
    return NormalizedComment(
        comment_id=str(row.get("id") or ""),
        docket_id=docket_id,
        posted_date=_str_or_none(attrs.get("postedDate")),
        submitter_name=_str_or_none(attrs.get("submitterName")),
        comment_text=_str_or_none(attrs.get("comment")),
    )


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
