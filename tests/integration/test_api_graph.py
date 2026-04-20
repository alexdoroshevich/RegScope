"""Integration tests for the citation graph API route."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_DOCKET = "EPA-HQ-OAR-2021-0317"


@pytest.mark.integration
class TestCitationGraph:
    def test_returns_200(self, api_client: TestClient) -> None:
        r = api_client.get(f"/api/v1/graph/{_DOCKET}")
        assert r.status_code == 200

    def test_response_schema(self, api_client: TestClient) -> None:
        body = api_client.get(f"/api/v1/graph/{_DOCKET}").json()
        assert "nodes" in body
        assert "links" in body

    def test_nodes_contain_docket(self, api_client: TestClient) -> None:
        nodes = api_client.get(f"/api/v1/graph/{_DOCKET}").json()["nodes"]
        docket_nodes = [n for n in nodes if n["type"] == "docket"]
        assert len(docket_nodes) == 1
        assert docket_nodes[0]["label"] == _DOCKET

    def test_nodes_contain_regulations(self, api_client: TestClient) -> None:
        nodes = api_client.get(f"/api/v1/graph/{_DOCKET}").json()["nodes"]
        reg_nodes = [n for n in nodes if n["type"] == "regulation"]
        assert len(reg_nodes) == 2  # 40 CFR Part 60 + 5 USC 553

    def test_cfr_node_label(self, api_client: TestClient) -> None:
        nodes = api_client.get(f"/api/v1/graph/{_DOCKET}").json()["nodes"]
        labels = {n["label"] for n in nodes}
        assert "40 CFR Part 60" in labels

    def test_links_connect_docket_to_regulations(self, api_client: TestClient) -> None:
        body = api_client.get(f"/api/v1/graph/{_DOCKET}").json()
        docket_id = f"docket:{_DOCKET}"
        sources = {lnk["source"] for lnk in body["links"]}
        assert sources == {docket_id}

    def test_link_value_is_comment_count(self, api_client: TestClient) -> None:
        body = api_client.get(f"/api/v1/graph/{_DOCKET}").json()
        cfr60_link = next(lnk for lnk in body["links"] if lnk["target"] == "CFR:40:60")
        # C-001 and C-002 both cite 40 CFR Part 60
        assert cfr60_link["value"] == 2

    def test_empty_docket_returns_empty_graph(self, api_client: TestClient) -> None:
        body = api_client.get("/api/v1/graph/NONEXISTENT-DOCKET").json()
        assert body["nodes"] == []
        assert body["links"] == []
