"""The unexpected-error handler must not log database messages or parameters."""

from __future__ import annotations

import logging

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

EMAIL = "leak@example.test"
PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$leak"


def _assert_clean_logs(caplog: pytest.LogCaptureFixture) -> str:
    logged = caplog.text
    assert EMAIL not in logged
    assert PASSWORD_HASH not in logged
    assert "23505" in logged
    assert "req-db" in logged
    return logged


def test_integrity_errors_log_only_class_sqlstate_and_request_id(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/explode-integrity")
    def explode_integrity() -> None:
        original = psycopg.errors.UniqueViolation(
            f"DETAIL: Key (email)=({EMAIL}) already exists; password_hash={PASSWORD_HASH}"
        )
        raise IntegrityError(
            f"INSERT INTO users (email, password_hash) VALUES ('{EMAIL}', '{PASSWORD_HASH}')",
            {"email": EMAIL, "password_hash": PASSWORD_HASH},
            original,
        )

    with caplog.at_level(logging.ERROR):
        response = TestClient(app, raise_server_exceptions=False).get(
            "/explode-integrity", headers={"X-Request-Id": "req-db"}
        )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    logged = _assert_clean_logs(caplog)
    assert "IntegrityError" in logged


def test_driver_errors_log_only_class_sqlstate_and_request_id(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/explode-driver")
    def explode_driver() -> None:
        raise psycopg.errors.UniqueViolation(
            f"DETAIL: Key (email)=({EMAIL}) already exists; password_hash={PASSWORD_HASH}"
        )

    with caplog.at_level(logging.ERROR):
        response = TestClient(app, raise_server_exceptions=False).get(
            "/explode-driver", headers={"X-Request-Id": "req-db"}
        )

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    logged = _assert_clean_logs(caplog)
    assert "UniqueViolation" in logged


def test_other_errors_still_log_their_message(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/explode-plain")
    def explode_plain() -> None:
        raise RuntimeError("plain failure")

    with caplog.at_level(logging.ERROR):
        response = TestClient(app, raise_server_exceptions=False).get("/explode-plain")

    assert response.status_code == 500
    assert "plain failure" in caplog.text


def test_database_error_logs_the_stack_frames_but_not_the_message(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.get("/explode-with-frames")
    def explode_with_frames() -> None:
        raise IntegrityError(
            "INSERT INTO users (email) VALUES (:email)",
            {"email": EMAIL},
            psycopg.errors.UniqueViolation(f"DETAIL: Key (email)=({EMAIL}) already exists"),
        )

    with caplog.at_level(logging.ERROR):
        TestClient(app, raise_server_exceptions=False).get(
            "/explode-with-frames", headers={"X-Request-Id": "req-db"}
        )

    assert "explode_with_frames" in caplog.text
    assert EMAIL not in caplog.text
    assert "already exists" not in caplog.text


def test_lock_timeout_logs_the_method_and_path_but_no_message(
    app: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    @app.post("/timed-out")
    def timed_out() -> None:
        raise psycopg.errors.LockNotAvailable("canceling statement due to lock timeout")

    with caplog.at_level(logging.WARNING):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/timed-out", headers={"X-Request-Id": "req-lock"}
        )

    assert response.status_code == 503
    assert "POST /timed-out" in caplog.text
    assert "req-lock" in caplog.text
    assert "canceling statement" not in caplog.text
