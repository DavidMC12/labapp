from __future__ import annotations

from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://labapp:labapp@localhost:5432/labapp"
    session_secret: str = "change-me"
    test_mode: bool = False
    test_token: str = ""
    default_tax_rate: Decimal = Decimal("10")
    app_origin: str = "http://localhost:3000"
    trusted_proxy_count: int = 0
