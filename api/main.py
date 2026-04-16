"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from api.config import get_settings
from api.logging_setup import configure_logging
from api.routes import astroturf, clusters, comments


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

    return application


app = create_app()
