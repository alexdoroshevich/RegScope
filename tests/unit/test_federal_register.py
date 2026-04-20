"""Unit tests for data.ingest.federal_register."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
import polars as pl
import pytest

from data.ingest.federal_register import (
    BASE_URL,
    DOCUMENT_COLUMNS,
    FederalRegisterClient,
    FederalRegisterError,
    NormalizedDocument,
    validate_documents,
    write_documents_parquet,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_httpx import HTTPXMock


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _page(
    docs: list[dict[str, Any]],
    total_pages: int = 1,
) -> dict[str, Any]:
    """Build a minimal Federal Register API response envelope."""
    return {"count": len(docs), "total_pages": total_pages, "results": docs}


def _doc(
    *,
    num: int = 1,
    pub_year: int = 2024,
    doc_type: str = "Rule",
    docket_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal Federal Register document dict."""
    return {
        "document_number": f"2024-{num:05d}",
        "title": f"Test Rule {num}",
        "type": doc_type,
        "abstract": f"Abstract for rule {num}.",
        "agency_names": ["Environmental Protection Agency"],
        "publication_date": f"{pub_year}-03-{num:02d}",
        "effective_on": f"{pub_year}-06-01",
        "comments_close_on": f"{pub_year}-04-30",
        "html_url": f"https://www.federalregister.gov/documents/{pub_year}/03/{num:02d}/test-rule-{num}",
        "citation": f"89 FR {10000 + num}",
        "significant": False,
        "docket_ids": docket_ids if docket_ids is not None else [f"EPA-HQ-OAR-2024-{num:04d}"],
    }


# ---------------------------------------------------------------------------
# NormalizedDocument / _normalize
# ---------------------------------------------------------------------------

def test_normalized_document_fields() -> None:
    """All dataclass fields match the Parquet schema columns."""
    doc = NormalizedDocument(
        document_number="2024-00001",
        docket_id="EPA-HQ-OAR-2024-0001",
        title="Test",
        doc_type="Rule",
        abstract=None,
        agency_names='["EPA"]',
        publication_date="2024-01-15",
        effective_on=None,
        comments_close_on=None,
        html_url=None,
        citation="89 FR 1234",
        significant=False,
    )
    assert doc.document_number == "2024-00001"
    assert doc.docket_id == "EPA-HQ-OAR-2024-0001"


# ---------------------------------------------------------------------------
# FederalRegisterClient.iter_documents
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iter_documents_single_page(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_page([_doc(num=1), _doc(num=2)]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert len(results) == 2
    assert results[0].document_number == "2024-00001"
    assert results[1].document_number == "2024-00002"


@pytest.mark.asyncio
async def test_iter_documents_paginates(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_page([_doc(num=1)], total_pages=3))
    httpx_mock.add_response(json=_page([_doc(num=2)], total_pages=3))
    httpx_mock.add_response(json=_page([_doc(num=3)], total_pages=3))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert [r.document_number for r in results] == [
        "2024-00001",
        "2024-00002",
        "2024-00003",
    ]


@pytest.mark.asyncio
async def test_iter_documents_empty_results(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_page([], total_pages=1))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert results == []


@pytest.mark.asyncio
async def test_docket_id_extracted_from_first_docket_ids_entry(
    httpx_mock: HTTPXMock,
) -> None:
    doc = _doc(num=1, docket_ids=["EPA-HQ-OAR-2024-0001", "EPA-HQ-OAR-2024-0002"])
    httpx_mock.add_response(json=_page([doc]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert results[0].docket_id == "EPA-HQ-OAR-2024-0001"


@pytest.mark.asyncio
async def test_docket_id_is_none_when_docket_ids_empty(
    httpx_mock: HTTPXMock,
) -> None:
    doc = _doc(num=1, docket_ids=[])
    httpx_mock.add_response(json=_page([doc]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert results[0].docket_id is None


@pytest.mark.asyncio
async def test_agency_names_stored_as_json(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(json=_page([_doc(num=1)]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=1) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    parsed = json.loads(results[0].agency_names)
    assert parsed == ["Environmental Protection Agency"]


# ---------------------------------------------------------------------------
# Retry / error handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retries_on_429_then_succeeds(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=429, json={"error": "rate limited"})
    httpx_mock.add_response(json=_page([_doc(num=1)]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=3) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert len(results) == 1


@pytest.mark.asyncio
async def test_raises_after_exhausting_retries(httpx_mock: HTTPXMock) -> None:
    for _ in range(3):
        httpx_mock.add_response(status_code=503, json={"error": "down"})

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=3) as client:
        with pytest.raises(FederalRegisterError):
            async for _ in client.iter_documents(since="2024-01-01"):
                pass


@pytest.mark.asyncio
async def test_raises_on_non_retryable_4xx(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(status_code=400, json={"error": "bad request"})

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=3) as client:
        with pytest.raises(FederalRegisterError):
            async for _ in client.iter_documents(since="2024-01-01"):
                pass


@pytest.mark.asyncio
async def test_retries_on_network_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    httpx_mock.add_response(json=_page([_doc(num=1)]))

    async with FederalRegisterClient(min_request_interval_s=0.0, max_retries=3) as client:
        results = [d async for d in client.iter_documents(since="2024-01-01")]

    assert len(results) == 1


# ---------------------------------------------------------------------------
# write_documents_parquet
# ---------------------------------------------------------------------------

def _make_doc(num: int, year: int = 2024) -> NormalizedDocument:
    return NormalizedDocument(
        document_number=f"2024-{num:05d}",
        docket_id=f"EPA-HQ-OAR-2024-{num:04d}",
        title=f"Rule {num}",
        doc_type="Rule",
        abstract=None,
        agency_names='["EPA"]',
        publication_date=f"{year}-03-{num:02d}",
        effective_on=None,
        comments_close_on=None,
        html_url=None,
        citation=f"89 FR {num}",
        significant=False,
    )


def test_write_documents_creates_parquet(tmp_path: Path) -> None:
    docs = [_make_doc(1), _make_doc(2)]
    stamp = datetime(2024, 6, 1, tzinfo=UTC)

    written = write_documents_parquet(docs, data_dir=tmp_path, fetched_at=stamp)

    assert 2024 in written
    assert written[2024].exists()
    df = pl.read_parquet(written[2024])
    assert df.height == 2
    assert set(df.columns) == set(DOCUMENT_COLUMNS)


def test_write_documents_partitions_by_year(tmp_path: Path) -> None:
    docs = [_make_doc(1, year=2023), _make_doc(2, year=2024)]

    written = write_documents_parquet(docs, data_dir=tmp_path)

    assert set(written.keys()) == {2023, 2024}
    assert pl.read_parquet(written[2023]).height == 1
    assert pl.read_parquet(written[2024]).height == 1


def test_write_documents_is_idempotent(tmp_path: Path) -> None:
    docs = [_make_doc(1)]

    write_documents_parquet(docs, data_dir=tmp_path)
    write_documents_parquet(docs, data_dir=tmp_path)  # second run overwrites

    df = pl.read_parquet(tmp_path / "documents" / "year=2024" / "part-00000.parquet")
    assert df.height == 1  # not doubled


def test_write_documents_doc_with_no_date_goes_to_year_zero(
    tmp_path: Path,
) -> None:
    doc = NormalizedDocument(
        document_number="2024-00001",
        docket_id=None,
        title="Undated Rule",
        doc_type="Rule",
        abstract=None,
        agency_names="[]",
        publication_date=None,
        effective_on=None,
        comments_close_on=None,
        html_url=None,
        citation=None,
        significant=None,
    )
    written = write_documents_parquet([doc], data_dir=tmp_path)
    assert 0 in written


# ---------------------------------------------------------------------------
# validate_documents
# ---------------------------------------------------------------------------

def test_validate_documents_raises_on_duplicate_document_number() -> None:
    from data.validation import SchemaValidationError

    stamp = datetime(2024, 1, 1, tzinfo=UTC)
    rows = [
        {**asdict(_make_doc(1)), "fetched_at": stamp},
        {**asdict(_make_doc(1)), "fetched_at": stamp},  # duplicate
    ]
    df = pl.DataFrame(rows, schema=DOCUMENT_COLUMNS)
    with pytest.raises(SchemaValidationError, match="duplicate"):
        validate_documents(df)
