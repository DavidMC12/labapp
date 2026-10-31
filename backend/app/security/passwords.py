"""Argon2id password hashing."""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from argon2.low_level import Type

_HASHER = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return _HASHER.hash(password)


def verify_password(hash: str, password: str) -> bool:
    """Verify a password, returning False for wrong passwords or malformed hashes."""
    if not isinstance(hash, str):
        return False
    try:
        return _HASHER.verify(hash, password)
    except (Argon2Error, TypeError, ValueError):
        # Every malformed hash must fail closed instead of raising.
        return False


def needs_rehash(hash: str) -> bool:
    """Return whether a valid hash uses parameters weaker than the current ones."""
    return _HASHER.check_needs_rehash(hash)
