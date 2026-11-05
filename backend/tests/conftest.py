# ruff: noqa: E402

import os

from app.config import Settings

for _name in ("DATABASE_URL", "DATABASE_URL_UNPOOLED", "DATABASE_SCHEMA"):
    os.environ.pop(_name, None)
Settings.model_config["env_file"] = None

os.environ.setdefault("SESSION_SECRET", "test-secret")

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
