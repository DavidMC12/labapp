"""Shared fixtures for the test-only controls endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def controls_settings() -> Settings:
    return Settings(session_secret="test-secret", test_mode=True)


@pytest.fixture
def controls_app(controls_settings: Settings) -> FastAPI:
    return create_app(controls_settings)


@pytest.fixture
def controls_client(controls_app: FastAPI) -> TestClient:
    return TestClient(controls_app)
