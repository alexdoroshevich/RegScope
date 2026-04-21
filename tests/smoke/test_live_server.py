"""Live-server smoke tests.

These tests hit a **running** FastAPI instance and frontend dev server
(not FastAPI's TestClient). Use them after a deploy or local startup to
verify that the binary + database + static assets are all wired up
correctly.

Typical usage — from the repo root, with the API on :8000 and Vite on
:5173 already running:

    uv run pytest tests/smoke -m smoke

The suite skips automatically if either server is unreachable, so it is
safe to include in the default unmarked run (where it is a no-op).

The tests assume the DB has been seeded with synthetic data via
``python -m scripts.seed_data`` (creates docket ``DEMO-2024-0001``).
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

API_URL = os.environ.get("FEDCOMMENT_SMOKE_API_URL", "http://localhost:8000")
UI_URL = os.environ.get("FEDCOMMENT_SMOKE_UI_URL", "http://localhost:5173")
SEED_DOCKET = "DEMO-2024-0001"

pytestmark = pytest.mark.smoke


def _get(path: str) -> httpx.Response:
    """GET a path on the API; skip the test if the API isn't running."""
    try:
        return httpx.get(f"{API_URL}{path}", timeout=5.0)
    except httpx.ConnectError as err:
        pytest.skip(f"API unreachable at {API_URL}: {err}")


# ───────── API surface ─────────


def test_api_health() -> None:
    r = _get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_api_dockets_list_has_seed_data() -> None:
    r = _get("/api/v1/dockets?limit=20")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1, "no dockets — run `python -m scripts.seed_data`"
    docket_ids = {item["docket_id"] for item in body["items"]}
    assert SEED_DOCKET in docket_ids, f"expected seed docket {SEED_DOCKET} in list"


def test_api_autocomplete_filters_by_query() -> None:
    r = _get("/api/v1/dockets?q=DEMO")
    assert r.status_code == 200
    body = r.json()
    assert all("DEMO" in item["docket_id"] for item in body["items"])


def test_api_astroturf_summary_is_populated() -> None:
    r = _get("/api/v1/astroturf/summary")
    assert r.status_code == 200
    s: dict[str, Any] = r.json()
    assert s["total_groups"] >= 1, "seed creates 3 duplicate groups"
    assert s["max_campaign_likelihood"] > 0


def test_api_astroturf_groups_list() -> None:
    r = _get("/api/v1/astroturf/groups?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    for g in body["items"]:
        assert g["group_size"] >= 1
        assert g["unique_submitters"] >= 1
        assert g["campaign_likelihood"] >= 0


def test_api_astroturf_group_comments_drilldown() -> None:
    # Fetch any existing group first. NOTE: we deliberately use ``limit=5``
    # here instead of ``limit=1`` to dodge a DuckDB 1.5.2 bug where
    # ``ORDER BY <numeric> DESC LIMIT 1`` returns an empty result set on
    # some tables. Tracked in DECISIONS.md / followup. The UI default is
    # limit=20 so real users never hit it.
    r = _get("/api/v1/astroturf/groups?limit=5")
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "need at least one group to drill into"
    group_id = items[0]["group_id"]
    r = _get(f"/api/v1/astroturf/groups/{group_id}/comments?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    for c in body:
        assert "comment_id" in c
        assert "comment_text" in c
        # submitter_name is optional (may be None)


def test_api_clusters_for_seed_docket() -> None:
    r = _get(f"/api/v1/clusters/{SEED_DOCKET}")
    assert r.status_code == 200
    clusters = r.json()
    assert isinstance(clusters, list)
    assert len(clusters) >= 1, "seed produces 7 clusters"
    # At least one cluster should have a label attached (seed runs the
    # labeller step synchronously).
    assert any(c["label"] for c in clusters), "expected at least one labelled cluster"


def test_api_graph_for_seed_docket() -> None:
    r = _get(f"/api/v1/graph/{SEED_DOCKET}")
    assert r.status_code == 200
    g = r.json()
    assert len(g["nodes"]) >= 1, "seed extracts 145 citations → graph should have nodes"
    assert len(g["links"]) >= 1


def test_api_openapi_schema_includes_all_routes() -> None:
    r = _get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = {
        "/health",
        "/api/v1/dockets",
        "/api/v1/astroturf/summary",
        "/api/v1/astroturf/groups",
        "/api/v1/clusters/{docket_id}",
        "/api/v1/graph/{docket_id}",
        "/api/v1/query",
    }
    missing = expected - paths.keys()
    assert not missing, f"missing routes in OpenAPI: {missing}"


# ───────── Frontend surface ─────────


def test_ui_serves_index_html() -> None:
    """Verify Vite is serving the SPA entrypoint."""
    try:
        r = httpx.get(UI_URL, timeout=5.0)
    except httpx.ConnectError as err:
        pytest.skip(f"UI unreachable at {UI_URL}: {err}")
    assert r.status_code == 200
    assert '<div id="root">' in r.text
    assert "FedComment" in r.text


def test_ui_no_legacy_regscope_references() -> None:
    """Make sure the rebrand didn't leave ``RegScope`` in the served HTML."""
    try:
        r = httpx.get(UI_URL, timeout=5.0)
    except httpx.ConnectError as err:
        pytest.skip(f"UI unreachable at {UI_URL}: {err}")
    assert r.status_code == 200
    assert "RegScope" not in r.text, "legacy RegScope branding present in served HTML"
