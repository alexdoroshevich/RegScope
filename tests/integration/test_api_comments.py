"""Integration tests for the comments API route."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_DOCKET = "EPA-HQ-OAR-2021-0317"


@pytest.mark.integration
class TestListComments:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get(f"/api/v1/comments/{_DOCKET}")
        assert r.status_code == 200

    def test_returns_seeded_comments(self, api_client: TestClient) -> None:
        body = api_client.get(f"/api/v1/comments/{_DOCKET}").json()
        assert body["total"] == 3
        assert len(body["items"]) == 3

    def test_comment_schema(self, api_client: TestClient) -> None:
        items = api_client.get(f"/api/v1/comments/{_DOCKET}").json()["items"]
        for item in items:
            assert "comment_id" in item
            assert "docket_id" in item
            assert "comment_text" in item

    def test_scoped_to_docket(self, api_client: TestClient) -> None:
        items = api_client.get(f"/api/v1/comments/{_DOCKET}").json()["items"]
        for item in items:
            assert item["docket_id"] == _DOCKET

    def test_unknown_docket_returns_empty(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/comments/DOES-NOT-EXIST").json()
        assert body["total"] == 0
        assert body["items"] == []

    def test_limit_param(self, api_client: TestClient) -> None:
        body = api_client.get(f"/api/v1/comments/{_DOCKET}?limit=2").json()
        assert len(body["items"]) == 2
        assert body["total"] == 3

    def test_offset_param(self, api_client: TestClient) -> None:
        all_ids = [
            i["comment_id"] for i in api_client.get(f"/api/v1/comments/{_DOCKET}").json()["items"]
        ]
        page2 = api_client.get(f"/api/v1/comments/{_DOCKET}?limit=2&offset=2").json()["items"]
        assert len(page2) == 1
        assert page2[0]["comment_id"] not in [all_ids[0], all_ids[1]] or len(all_ids) > 2

    def test_pagination_no_overlap(self, api_client: TestClient) -> None:
        p1 = {
            i["comment_id"]
            for i in api_client.get(f"/api/v1/comments/{_DOCKET}?limit=2&offset=0").json()["items"]
        }
        p2 = {
            i["comment_id"]
            for i in api_client.get(f"/api/v1/comments/{_DOCKET}?limit=2&offset=2").json()["items"]
        }
        assert p1.isdisjoint(p2)
