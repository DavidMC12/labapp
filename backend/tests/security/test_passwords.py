"""Tests for Argon2id password hashing."""

from __future__ import annotations

import pytest
from argon2 import PasswordHasher

from app.security.passwords import hash_password, needs_rehash, verify_password

PASSWORD = "Demo-LabApp-2026!"


def test_hash_and_verify_round_trip() -> None:
    hashed = hash_password(PASSWORD)

    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, PASSWORD) is True


def test_wrong_password_is_rejected() -> None:
    hashed = hash_password(PASSWORD)

    assert verify_password(hashed, "not-the-password") is False


@pytest.mark.parametrize(
    "malformed",
    [
        "",
        "not-a-hash",
        "$argon2id$garbage",
        "$argon2id$v=19$m=65536,t=3,p=4$abc$def",
        "ü",
    ],
)
def test_malformed_hash_returns_false(malformed: str) -> None:
    assert verify_password(malformed, PASSWORD) is False


def test_non_ascii_password_round_trip() -> None:
    password = "contraseña-segura"
    hashed = hash_password(password)

    assert verify_password(hashed, password) is True
    assert verify_password(hashed, "contrasena-segura") is False


def test_two_hashes_of_the_same_password_differ() -> None:
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_fresh_hash_does_not_need_a_rehash() -> None:
    assert needs_rehash(hash_password(PASSWORD)) is False


def test_hash_with_weaker_parameters_needs_a_rehash() -> None:
    weaker_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    weaker_hash = weaker_hasher.hash(PASSWORD)

    assert verify_password(weaker_hash, PASSWORD) is True
    assert needs_rehash(weaker_hash) is True


@pytest.mark.parametrize("malformed", [None, 42, b"$argon2id$garbage"])
def test_a_non_string_hash_returns_false(malformed: object) -> None:
    assert verify_password(malformed, PASSWORD) is False  # type: ignore[arg-type]
