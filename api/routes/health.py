"""Health-check endpoint — used by Docker HEALTHCHECK and load-balancers."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=True)
def health_check() -> dict[str, str]:
    """Return API liveness status."""
    return {"status": "ok"}
