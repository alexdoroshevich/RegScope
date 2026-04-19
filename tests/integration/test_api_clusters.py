"""Integration tests for the clusters API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_DOCKET = "EPA-HQ-OAR-2021-0317"


@pytest.mark.integration
class TestListClusters:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get(f"/api/v1/clusters/{_DOCKET}")
        assert r.status_code == 200

    def test_returns_seeded_clusters(self, api_client: TestClient) -> None:
        clusters = api_client.get(f"/api/v1/clusters/{_DOCKET}").json()
        assert len(clusters) == 2

    def test_comment_counts_correct(self, api_client: TestClient) -> None:
        clusters = api_client.get(f"/api/v1/clusters/{_DOCKET}").json()
        counts = {c["cluster_id"]: c["comment_count"] for c in clusters}
        assert counts[0] == 2
        assert counts[1] == 1

    def test_labeled_cluster_has_label(self, api_client: TestClient) -> None:
        clusters = api_client.get(f"/api/v1/clusters/{_DOCKET}").json()
        labeled = next(c for c in clusters if c["cluster_id"] == 0)
        assert labeled["label"] == "Clean air support"
        assert "supporting clean-air" in labeled["summary"]

    def test_unlabeled_cluster_has_null_label(self, api_client: TestClient) -> None:
        clusters = api_client.get(f"/api/v1/clusters/{_DOCKET}").json()
        unlabeled = next(c for c in clusters if c["cluster_id"] == 1)
        assert unlabeled["label"] is None

    def test_unknown_docket_returns_empty(self, api_client: TestClient) -> None:
        clusters = api_client.get("/api/v1/clusters/DOES-NOT-EXIST").json()
        assert clusters == []

    def test_ordered_by_comment_count_desc(self, api_client: TestClient) -> None:
        clusters = api_client.get(f"/api/v1/clusters/{_DOCKET}").json()
        counts = [c["comment_count"] for c in clusters]
        assert counts == sorted(counts, reverse=True)


@pytest.mark.integration
class TestClusterComments:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get(f"/api/v1/clusters/{_DOCKET}/0")
        assert r.status_code == 200

    def test_returns_comments_for_cluster(self, api_client: TestClient) -> None:
        comments = api_client.get(f"/api/v1/clusters/{_DOCKET}/0").json()
        assert len(comments) == 2
        ids = {c["comment_id"] for c in comments}
        assert ids == {"C-001", "C-002"}

    def test_comment_schema(self, api_client: TestClient) -> None:
        comments = api_client.get(f"/api/v1/clusters/{_DOCKET}/0").json()
        for c in comments:
            assert "comment_id" in c
            assert "comment_text" in c
            assert "submitter_name" in c

    def test_empty_for_unknown_cluster(self, api_client: TestClient) -> None:
        comments = api_client.get(f"/api/v1/clusters/{_DOCKET}/999").json()
        assert comments == []

    def test_limit_param(self, api_client: TestClient) -> None:
        comments = api_client.get(f"/api/v1/clusters/{_DOCKET}/0?limit=1").json()
        assert len(comments) == 1
