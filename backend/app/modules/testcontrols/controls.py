"""Load the clock offset and one fault decision for a request."""

from __future__ import annotations

from sqlalchemy.engine import Engine

from app.modules.testcontrols.models import FaultDecision
from app.modules.testcontrols.ports import ClockOffsetStore, FaultStore


class RequestControls:
    """The per-request controls loader used by the ASGI middleware.

    In PostgreSQL mode ``load_request_controls`` opens one transaction and passes it
    to both stores, so a request reads its offset and consumes its fault through the
    same connection. In memory mode it is a plain call with no thread hop.
    """

    def __init__(
        self,
        clock_store: ClockOffsetStore,
        fault_store: FaultStore,
        engine: Engine | None = None,
    ) -> None:
        self._clock_store = clock_store
        self._fault_store = fault_store
        self._engine = engine

    @property
    def uses_threadpool(self) -> bool:
        """Return whether the stores are the PostgreSQL ones."""
        return self._engine is not None

    def load_request_controls(self, method: str, path: str) -> tuple[float, FaultDecision | None]:
        """Return the clock offset and the fault decision of this request."""
        if self._engine is None:
            return (
                self._clock_store.get(),
                self._fault_store.take(method, path),
            )

        with self._engine.begin() as connection:
            return (
                self._clock_store.get(connection=connection),
                self._fault_store.take(method, path, connection=connection),
            )
