from __future__ import annotations

from fastapi import FastAPI

from app.config import Settings

DEFAULT_SESSION_SECRET = "change-me"


def _check_session_secret(settings: Settings) -> None:
    if settings.test_mode:
        return
    if settings.session_secret.strip() in ("", DEFAULT_SESSION_SECRET):
        raise RuntimeError(
            "SESSION_SECRET must be set to a strong value: it is empty or still 'change-me'. "
            "Set SESSION_SECRET in the environment, or TEST_MODE=1 for local tests only."
        )


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application."""
    settings = settings if settings is not None else Settings()
    _check_session_secret(settings)

    app = FastAPI(title="LabApp API")
    app.state.settings = settings

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
