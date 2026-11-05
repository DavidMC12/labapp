"""Authentication container wiring."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.config import Settings
from app.infra.clock import OffsetClock
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.ports import SessionStore, UserRepository
from app.modules.auth.seed import demo_password_hash, dummy_hash, seed_users
from app.modules.auth.service import AuthService


@dataclass(frozen=True)
class Container:
    """The auth dependencies shared by one application instance."""

    settings: Settings = field(repr=False)
    clock: OffsetClock
    users: UserRepository
    sessions: SessionStore
    auth: AuthService


def build_container(settings: Settings, clock: OffsetClock) -> Container:
    """Build the in-memory adapters and the auth service."""
    users = InMemoryUserRepository(seed_users(demo_password_hash()))
    sessions = InMemorySessionStore()
    auth = AuthService(users, sessions, clock, dummy_hash=dummy_hash())
    return Container(
        settings=settings,
        clock=clock,
        users=users,
        sessions=sessions,
        auth=auth,
    )
