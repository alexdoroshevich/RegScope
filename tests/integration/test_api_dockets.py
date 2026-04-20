"""Integration tests for GET /api/v1/dockets."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# conftest seeds EPA-HQ-OAR-2021-0317 (3 comments) and OTHER-DOCKET (1 comment).
_MAIN_DOCKET = "EPA-HQ-OAR-2021-0317"
_OTHER_DOCKET = "OTHER-DOCKET"


@pytest.mark.integration
class TestDocketsEndpoint:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get("/api/v1/dockets")
        assert r.status_code == 200

    def test_response_schema(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets").json()
        assert "items" in body
        assert "total" in body
        assert "limit" in body
        assert "offset" in body

    def test_lists_both_seeded_dockets(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets").json()
        docket_ids = {d["docket_id"] for d in body["items"]}
        assert _MAIN_DOCKET in docket_ids
        assert _OTHER_DOCKET in docket_ids

    def test_ordered_by_comment_count_desc(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets").json()
        counts = [d["comment_count"] for d in body["items"]]
        assert counts == sorted(counts, reverse=True)

    def test_main_docket_has_correct_count(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets").json()
        main = next(d for d in body["items"] if d["docket_id"] == _MAIN_DOCKET)
        assert main["comment_count"] == 3

    def test_search_filter_returns_matching_dockets(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets", params={"q": "EPA"}).json()
        docket_ids = {d["docket_id"] for d in body["items"]}
        assert _MAIN_DOCKET in docket_ids
        assert _OTHER_DOCKET not in docket_ids

    def test_search_filter_is_case_insensitive(self, api_client: TestClient) -> None:
        lower = api_client.get("/api/v1/dockets", params={"q": "epa"}).json()
        upper = api_client.get("/api/v1/dockets", params={"q": "EPA"}).json()
        assert {d["docket_id"] for d in lower["items"]} == {
            d["docket_id"] for d in upper["items"]
        }

    def test_search_no_match_returns_empty(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets", params={"q": "NOMATCH-XYZ"}).json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_limit_respected(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets", params={"limit": 1}).json()
        assert len(body["items"]) == 1

    def test_total_reflects_full_count_not_page(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/dockets", params={"limit": 1}).json()
        assert body["total"] == 2  # seed has 2 distinct dockets
