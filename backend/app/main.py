"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.health import check_database_connection


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    try:
        get_settings()
    except ValidationError as exc:
        logger.critical("Application configuration is invalid: %s", exc)
        raise RuntimeError("Application configuration is invalid.") from exc

    application = FastAPI(
        title="Smart AI Problem-to-Impact API",
        version="0.1.0",
        description="Backend foundation for the Smart AI Problem-to-Impact platform.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Report whether the API process is running."""

        return {"status": "ok", "message": "Backend is running"}

    @application.get("/api/health/db", tags=["health"])
    def database_health_check() -> dict[str, str]:
        """Report whether the configured PostgreSQL database is reachable."""

        if not check_database_connection():
            raise HTTPException(
                status_code=503,
                detail="Database connection failed. Check configuration and database availability.",
            )

        return {"status": "ok", "database": "connected"}

    return application


app = create_app()