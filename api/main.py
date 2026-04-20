"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.config import get_settings
from api.logging_setup import configure_logging
from api.routes import astroturf, clusters, comments, dockets, graph, health, query

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="RegScope API",
        description="Regulatory intelligence — astroturf detection and comment clustering.",
        version="0.1.0",
    )

    application.include_router(health.router)
    application.include_router(comments.router, prefix="/api/v1")
    application.include_router(clusters.router, prefix="/api/v1")
    application.include_router(astroturf.router, prefix="/api/v1")
    application.include_router(graph.router, prefix="/api/v1")
    application.include_router(query.router, prefix="/api/v1")
    application.include_router(dockets.router, prefix="/api/v1")

    if _FRONTEND_DIST.is_dir():
        # html=True enables SPA fallback: unknown paths → index.html.
        # No user input touches the filesystem; StaticFiles handles path resolution internally.
        application.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="spa")

    return application


app = create_app()
