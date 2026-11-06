"""Authentication container wiring."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.engine import Engine

from app.config import Settings
from app.infra.clock import OffsetClock
from app.modules.auth.adapters.memory import InMemorySessionStore, InMemoryUserRepository
from app.modules.auth.adapters.postgres import PostgresSessionStore, PostgresUserRepository
from app.modules.auth.ports import SessionStore, UserRepository
from app.modules.auth.seed import demo_password_hash, dummy_hash, seed_users
from app.modules.auth.service import AuthService
from app.security.ratelimit import GENERAL_LIMIT, LOGIN_LIMIT, SlidingWindowLimiter


@dataclass(frozen=True)
class Limiters:
    """The rate limiters shared by one application instance."""

    general: SlidingWindowLimiter
    login: SlidingWindowLimiter

    def reset(self) -> None:
        """Forget every counted request."""
        self.general.clear()
        self.login.clear()


@dataclass(frozen=True)
class Container:
    """The auth dependencies shared by one application instance."""

    settings: Settings = field(repr=False)
    clock: OffsetClock
    users: UserRepository
    sessions: SessionStore
    auth: AuthService
    limiters: Limiters

    def reset_limiters(self) -> None:
        """Clear both rate limiters."""
        self.limiters.reset()


def build_container(
    settings: Settings,
    clock: OffsetClock,
    *,
    engine: Engine | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> Container:
    """Build the adapters selected by the settings and the auth service."""
    users: UserRepository
    sessions: SessionStore
    if engine is None:
        users = InMemoryUserRepository(seed_users(demo_password_hash()))
        sessions = InMemorySessionStore()
    else:
        users = PostgresUserRepository(engine)
        sessions = PostgresSessionStore(engine)
    auth = AuthService(users, sessions, clock, dummy_hash=dummy_hash())
    limiters = Limiters(
        general=SlidingWindowLimiter(GENERAL_LIMIT[0], GENERAL_LIMIT[1], clock=monotonic),
        login=SlidingWindowLimiter(LOGIN_LIMIT[0], LOGIN_LIMIT[1], clock=monotonic),
    )
    return Container(
        settings=settings,
        clock=clock,
        users=users,
        sessions=sessions,
        auth=auth,
        limiters=limiters,
    )
