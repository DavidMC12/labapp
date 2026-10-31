# ruff: noqa: E402

import os

os.environ.setdefault("SESSION_SECRET", "test-secret")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(session_secret="test-secret", test_mode=False)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
