"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.health import check_database_connection
from app.db.session import SessionLocal
from app.routes.organizations import router as organizations_router
from app.routes.government_profiles import router as government_profiles_router
from app.routes.auth import router as auth_router
from app.routes.users import router as users_router
from app.routes.problems import router as problems_router
from app.routes.similarity import router as similarity_router
from app.routes.validation import router as validation_router
from app.routes.ai_analysis import router as ai_analysis_router
from app.routes.capability import capability_router, taxonomy_router
from app.routes.hei import router as hei_router
from app.routes.evidence import router as evidence_router
from app.routes.partner import router as partner_router


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
        description="Backend for the Smart AI Problem-to-Impact platform.",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register all routers ───────────────────────────────────────────────────
    application.include_router(organizations_router)
    application.include_router(government_profiles_router)
    application.include_router(auth_router)
    application.include_router(users_router)
    application.include_router(problems_router)
    application.include_router(similarity_router)
    application.include_router(validation_router)
    application.include_router(ai_analysis_router)
    application.include_router(capability_router)
    application.include_router(taxonomy_router)
    application.include_router(hei_router)
    application.include_router(evidence_router)
    application.include_router(partner_router)

    # ── Startup: seed capability data ──────────────────────────────────────────
    @application.on_event("startup")
    def seed_on_startup() -> None:
        try:
            from app.services.seed import seed_capabilities
            db = SessionLocal()
            try:
                seed_capabilities(db)
            finally:
                db.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Seed data step skipped or failed: %s", exc)

    # ── Health endpoints ───────────────────────────────────────────────────────
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
                detail="Database connection failed.",
            )
        return {"status": "ok", "database": "connected"}

    return application


app = create_app()
