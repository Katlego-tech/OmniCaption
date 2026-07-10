"""FastAPI application factory for the OmniCaption backend API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import AuthService
from app.core.config import Settings
from app.core.runner import PipelineRunner
from app.routers import auth, keys, media, qa, results, search, tasks


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app around a settings instance (injectable for tests).

    Args:
        settings: Pre-built settings; read from the environment when omitted.
    """
    settings = settings or Settings()

    app = FastAPI(title="OmniCaption API", version="0.1.0")
    app.state.settings = settings
    app.state.runner = PipelineRunner()
    app.state.auth = AuthService(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(results.router, prefix="/api/results", tags=["results"])
    app.include_router(search.router, prefix="/api/search", tags=["search"])
    app.include_router(qa.router, prefix="/api/qa", tags=["qa"])
    app.include_router(media.router, prefix="/api/media", tags=["media"])
    app.include_router(keys.router, prefix="/api/keys", tags=["keys"])
    app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok", "service": "omnicaption-api"}

    return app


app = create_app()
