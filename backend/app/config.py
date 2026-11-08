from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal
from os import environ
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SCHEMA_PATTERN = re.compile(r"[a-z_][a-z0-9_]{0,62}")
_RESERVED_SCHEMAS = frozenset({"public", "information_schema"})
_ORIGIN_SCHEMES = frozenset({"http", "https"})


def _origin_key(value: str) -> tuple[str, str, int]:
    parts = urlsplit(value)
    port = parts.port
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    return (parts.scheme.lower(), (parts.hostname or "").lower(), port)


def _is_valid_origin(value: str) -> bool:
    """Return whether the value is exactly scheme://host[:port] with no path."""
    if any(character.isspace() for character in value):
        return False
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError:
        return False
    return (
        parts.scheme in _ORIGIN_SCHEMES
        and bool(parts.netloc)
        and parts.hostname is not None
        and parts.username is None
        and parts.password is None
        and not parts.path
        and not parts.query
        and not parts.fragment
    )


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
    lock_timeout_ms: int = Field(default=5000, ge=100, le=60000)
    vercel_url: str | None = None
    vercel_branch_url: str | None = None
    vercel_project_production_url: str | None = None

    @field_validator(
        "database_url",
        "database_url_unpooled",
        "database_schema",
        "vercel_url",
        "vercel_branch_url",
        "vercel_project_production_url",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value

    @model_validator(mode="after")
    def _refuse_test_mode_on_vercel(self) -> Settings:
        """Keep TEST_MODE off in every public deployment."""
        if self.test_mode and environ.get("VERCEL_ENV") in ("production", "preview"):
            raise ValueError("TEST_MODE must be off on a Vercel deployment")
        return self

    @property
    def allowed_origins(self) -> tuple[str, ...]:
        """Return the validated origins a state-changing request may come from."""
        candidates = [self.app_origin]
        for host in (
            self.vercel_url,
            self.vercel_branch_url,
            self.vercel_project_production_url,
        ):
            if host:
                candidates.append(f"https://{host}")
        origins = [candidate for candidate in candidates if _is_valid_origin(candidate)]
        unique: list[str] = []
        seen: set[tuple[str, str, int]] = set()
        for origin in origins:
            key = _origin_key(origin)
            if key in seen:
                continue
            seen.add(key)
            unique.append(origin)
        return tuple(unique)

    @field_validator("default_tax_rate")
    @classmethod
    def _validate_default_tax_rate(cls, value: Decimal) -> Decimal:
        """Keep the initial tax rate a percentage with two decimals, as the spec says."""
        rate = (
            value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if value.is_finite() else value
        )
        if not rate.is_finite() or not Decimal("0.00") <= rate <= Decimal("100.00"):
            raise ValueError("Invalid default tax rate")
        return rate

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
