from __future__ import annotations

import re
from decimal import Decimal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SCHEMA_PATTERN = re.compile(r"[a-z_][a-z0-9_]{0,62}")
_RESERVED_SCHEMAS = frozenset({"public", "information_schema"})


class Settings(BaseSettings):
    """Application configuration read from environment variables."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: str | None = Field(default=None, repr=False)
    database_url_unpooled: str | None = Field(default=None, repr=False)
    database_schema: str | None = None
    session_secret: str = Field(default="change-me", repr=False)
    test_mode: bool = False
    test_token: str = Field(default="", repr=False)
    default_tax_rate: Decimal = Decimal("10")
    app_origin: str = "http://localhost:3000"
    trusted_proxy_count: int = 0

    @field_validator("database_url", "database_url_unpooled", "database_schema", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @field_validator("database_schema")
    @classmethod
    def _validate_schema(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if (
            _SCHEMA_PATTERN.fullmatch(value) is None
            or value in _RESERVED_SCHEMAS
            or value.startswith("pg_")
        ):
            raise ValueError("Invalid database schema")
        return value
