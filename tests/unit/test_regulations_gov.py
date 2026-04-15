"""Unit tests for data.ingest.regulations_gov."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
import pytest

from data.ingest.regulations_gov import (
    BASE_URL,
    NormalizedComment,
    RegulationsGovClient,
    RegulationsGovError,
)

if TYPE_CHECKING:
    from pytest_httpx import HTTPXMock


def _page(rows: int, *, start: int = 1, page_size: int = 250) -> dict[str, Any]:
    return {
        "data": [
            {
                "id": f"EPA-HQ-TEST-{start + i:04d}",
                "type": "comments",
                "attributes": {
                    "postedDate": f"2024-03-{(i % 28) + 1:02d}T12:00:00Z",
                    "submitterName": f"Commenter {start + i}",
                    "comment": f"comment body {start + i}",
                },
            }
            for i in range(rows)
        ],
        "meta": {"totalElements": rows, "pageSize": page_size, "pageNumber": 1},
    }


@pytest.mark.asyncio
async def test_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError):
        RegulationsGovClient("")


@pytest.mark.asyncio
async def test_iter_comments_single_page(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=(
            f"{BASE_URL}/comments"
            "?filter%5BdocketId%5D=EPA-HQ-OAR-2021-0317"
            "&page%5Bnumber%5D=1&page%5Bsize%5D=3&sort=postedDate"
        ),
        json=_page(2, page_size=3),
    )
    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=1) as client:
        results = [c async for c in client.iter_comments("EPA-HQ-OAR-2021-0317", page_size=3)]

    assert len(results) == 2
    assert results[0] == NormalizedComment(
        comment_id="EPA-HQ-TEST-0001",
        docket_id="EPA-HQ-OAR-2021-0317",
        posted_date="2024-03-01T12:00:00Z",
        submitter_name="Commenter 1",
        comment_text="comment body 1",
    )


@pytest.mark.asyncio
async def test_iter_comments_paginates(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_page(3, start=1, page_size=3))
    httpx_mock.add_response(json=_page(3, start=4, page_size=3))
    httpx_mock.add_response(json=_page(1, start=7, page_size=3))

    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=1) as client:
        results = [c async for c in client.iter_comments("D-1", page_size=3)]

    assert [r.comment_id for r in results] == [
        "EPA-HQ-TEST-0001",
        "EPA-HQ-TEST-0002",
        "EPA-HQ-TEST-0003",
        "EPA-HQ-TEST-0004",
        "EPA-HQ-TEST-0005",
        "EPA-HQ-TEST-0006",
        "EPA-HQ-TEST-0007",
    ]


@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, json={"error": "rate"})
    httpx_mock.add_response(json=_page(1, page_size=10))

    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=3) as client:
        results = [c async for c in client.iter_comments("D-1", page_size=10)]

    assert len(results) == 1


@pytest.mark.asyncio
async def test_raises_after_exhausting_retries(httpx_mock: HTTPXMock) -> None:
    for _ in range(3):
        httpx_mock.add_response(status_code=503, json={"error": "down"})

    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=3) as client:
        with pytest.raises(RegulationsGovError):
            async for _ in client.iter_comments("D-1", page_size=10):
                pass


@pytest.mark.asyncio
async def test_raises_on_non_retryable_4xx(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=401, json={"error": "unauthorized"})

    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=3) as client:
        with pytest.raises(RegulationsGovError):
            async for _ in client.iter_comments("D-1", page_size=10):
                pass


@pytest.mark.asyncio
async def test_retries_on_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    httpx_mock.add_response(json=_page(1, page_size=10))

    async with RegulationsGovClient("key", min_request_interval_s=0.0, max_retries=3) as client:
        results = [c async for c in client.iter_comments("D-1", page_size=10)]

    assert len(results) == 1
