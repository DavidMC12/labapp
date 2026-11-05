from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings
from app.errors import register_error_handlers
from app.infra.clock import OffsetClock, SystemClock
from app.middleware import BodySizeLimitMiddleware, RequestIdMiddleware
from app.modules.auth.container import build_container
from app.modules.auth.routes import router as auth_router

DEFAULT_SESSION_SECRET = "change-me"


def _check_session_secret(settings: Settings) -> None:
    if settings.test_mode:
        return
    if settings.session_secret.strip() in ("", DEFAULT_SESSION_SECRET):
        raise RuntimeError(
            "SESSION_SECRET must be set to a strong value: it is empty or still 'change-me'. "
            "Set SESSION_SECRET in the environment, or TEST_MODE=1 for local tests only."
        )


def create_app(
    settings: Settings | None = None,
    *,
    clock: OffsetClock | None = None,
) -> FastAPI:
    """Build the FastAPI application."""
    settings = settings if settings is not None else Settings()
    _check_session_secret(settings)

    application_clock = clock if clock is not None else OffsetClock(SystemClock())
    container = build_container(settings, application_clock)

    app = FastAPI(title="LabApp API")
    app.state.settings = settings
    app.state.container = container
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(auth_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
