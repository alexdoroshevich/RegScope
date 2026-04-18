"""FastAPI application factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import get_settings
from api.logging_setup import configure_logging
from api.routes import astroturf, clusters, comments

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

    application.include_router(comments.router, prefix="/api/v1")
    application.include_router(clusters.router, prefix="/api/v1")
    application.include_router(astroturf.router, prefix="/api/v1")

    if _FRONTEND_DIST.is_dir():
        application.mount(
            "/assets", StaticFiles(directory=_FRONTEND_DIST / "assets"), name="assets"
        )

        _index = _FRONTEND_DIST / "index.html"

        @application.get("/{full_path:path}")
        async def _spa_fallback(full_path: str) -> FileResponse:
            """Serve index.html for all non-API routes (SPA client-side routing)."""
            if ".." in full_path or full_path.startswith("api/"):
                return FileResponse(_index)
            file = (_FRONTEND_DIST / full_path).resolve()
            if file.is_relative_to(_FRONTEND_DIST) and file.is_file():
                return FileResponse(file)
            return FileResponse(_index)

    return application


app = create_app()
