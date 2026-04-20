"""Integration tests for the astroturf API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAstroturfSummary:
    def test_summary_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get("/api/v1/astroturf/summary")
        assert r.status_code == 200

    def test_summary_counts(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/astroturf/summary").json()
        assert body["total_groups"] == 2
        assert body["astroturf_groups"] == 1
        assert body["total_flagged_comments"] == 3  # group_size 2 + 1
        assert body["max_campaign_likelihood"] == pytest.approx(1.0)

    def test_summary_schema(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/astroturf/summary").json()
        for key in (
            "total_groups",
            "astroturf_groups",
            "total_flagged_comments",
            "max_campaign_likelihood",
        ):
            assert key in body


@pytest.mark.integration
class TestAstroturfGroups:
    def test_groups_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get("/api/v1/astroturf/groups")
        assert r.status_code == 200

    def test_groups_all(self, api_client: TestClient) -> None:
        items = api_client.get("/api/v1/astroturf/groups").json()["items"]
        assert len(items) == 2

    def test_groups_astroturf_only_filter(self, api_client: TestClient) -> None:
        items = api_client.get("/api/v1/astroturf/groups?astroturf_only=true").json()["items"]
        assert len(items) >= 1
        for item in items:
            assert item["is_astroturf"] is True

    def test_groups_ordered_by_likelihood_desc(self, api_client: TestClient) -> None:
        items = api_client.get("/api/v1/astroturf/groups").json()["items"]
        likelihoods = [i["campaign_likelihood"] for i in items]
        assert likelihoods == sorted(likelihoods, reverse=True)

    def test_groups_pagination(self, api_client: TestClient) -> None:
        ids1 = {
            i["group_id"]
            for i in api_client.get("/api/v1/astroturf/groups?limit=1&offset=0").json()["items"]
        }
        ids2 = {
            i["group_id"]
            for i in api_client.get("/api/v1/astroturf/groups?limit=1&offset=1").json()["items"]
        }
        assert ids1.isdisjoint(ids2)

    def test_groups_item_schema(self, api_client: TestClient) -> None:
        item = api_client.get("/api/v1/astroturf/groups?limit=1").json()["items"][0]
        for key in (
            "group_id",
            "group_size",
            "unique_submitters",
            "campaign_likelihood",
            "is_astroturf",
        ):
            assert key in item

    def test_groups_total_field(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/astroturf/groups").json()
        assert body["total"] == 2


@pytest.mark.integration
class TestGroupComments:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get("/api/v1/astroturf/groups/1/comments")
        assert r.status_code == 200

    def test_returns_correct_comments(self, api_client: TestClient) -> None:
        data = api_client.get("/api/v1/astroturf/groups/1/comments").json()
        ids = {c["comment_id"] for c in data}
        assert ids == {"C-001", "C-002"}

    def test_single_comment_group(self, api_client: TestClient) -> None:
        data = api_client.get("/api/v1/astroturf/groups/2/comments").json()
        assert len(data) == 1
        assert data[0]["comment_id"] == "C-003"

    def test_comment_schema(self, api_client: TestClient) -> None:
        item = api_client.get("/api/v1/astroturf/groups/1/comments").json()[0]
        assert "comment_id" in item
        assert "comment_text" in item
        assert "submitter_name" in item

    def test_limit_param(self, api_client: TestClient) -> None:
        data = api_client.get("/api/v1/astroturf/groups/1/comments?limit=1").json()
        assert len(data) == 1

    def test_unknown_group_returns_404(self, api_client: TestClient) -> None:
        r = api_client.get("/api/v1/astroturf/groups/999/comments")
        assert r.status_code == 404
