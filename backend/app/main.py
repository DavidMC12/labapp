from __future__ import annotations

import time
from collections.abc import Callable
from threading import RLock

from fastapi import Depends, FastAPI

from app.config import Settings
from app.domain.money import quantize_money
from app.errors import register_error_handlers
from app.guards.controls import ControlsGuardMiddleware
from app.guards.origin import origin_guard
from app.guards.ratelimit_middleware import RateLimitMiddleware
from app.guards.request_controls import RequestControlsMiddleware
from app.infra.clock import Clock, ControlledClock, OffsetClock, SystemClock
from app.infra.db import create_db_engine
from app.middleware import BodySizeLimitMiddleware, RequestIdMiddleware
from app.modules.auth.container import build_container
from app.modules.auth.routes import router as auth_router
from app.modules.customers.adapters.memory import InMemoryCustomerRepository
from app.modules.customers.adapters.postgres import PostgresCustomerRepository
from app.modules.customers.routes import router as customers_router
from app.modules.customers.seed import seed_customers
from app.modules.customers.service import CustomerService
from app.modules.invoices.adapters.memory import InMemoryInvoiceStore
from app.modules.invoices.adapters.postgres import PostgresInvoiceStore
from app.modules.invoices.gateway import FakeGateway, FaultyGateway
from app.modules.invoices.mail import LoggingMailer
from app.modules.invoices.routes import router as invoices_router
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.invoices.service import InvoiceService
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.routes import router as orders_router
from app.modules.orders.seed import seed_orders, seed_products
from app.modules.orders.service import OrderService
from app.modules.testcontrols.controls import RequestControls
from app.modules.testcontrols.memory import (
    InMemoryClockOffsetStore,
    InMemoryFaultStore,
)
from app.modules.testcontrols.postgres import (
    PostgresClockOffsetStore,
    PostgresFaultStore,
)
from app.modules.testcontrols.reset import MemoryResetter, PostgresResetter
from app.modules.testcontrols.routes import router as testcontrols_router

DEFAULT_SESSION_SECRET = "change-me"


def _check_session_secret(settings: Settings) -> None:
    if settings.test_mode:
        return
    if settings.session_secret.strip() in ("", DEFAULT_SESSION_SECRET):
        raise RuntimeError(
            "SESSION_SECRET must be set to a strong value: it is empty or still 'change-me'. "
            "Set SESSION_SECRET in the environment, or TEST_MODE=1 for local tests only."
        )


def create_app(
    settings: Settings | None = None,
    *,
    clock: OffsetClock | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> FastAPI:
    """Build the FastAPI application."""
    settings = settings if settings is not None else Settings()
    _check_session_secret(settings)

    base_clock = clock if clock is not None else OffsetClock(SystemClock())
    database_engine = create_db_engine(settings) if settings.database_url is not None else None
    controls_enabled = settings.test_mode or bool(settings.test_token)
    clock_store: InMemoryClockOffsetStore | PostgresClockOffsetStore
    fault_store: InMemoryFaultStore | PostgresFaultStore
    application_clock: Clock
    if database_engine is None:
        clock_store = InMemoryClockOffsetStore(base_clock)
        fault_store = InMemoryFaultStore()
        application_clock = base_clock
    else:
        clock_store = PostgresClockOffsetStore(database_engine)
        fault_store = PostgresFaultStore(database_engine)
        application_clock = ControlledClock(base_clock, clock_store, controls_enabled)
    request_controls = RequestControls(clock_store, fault_store, database_engine)

    container = build_container(
        settings,
        application_clock,
        engine=database_engine,
        monotonic=monotonic,
    )
    if database_engine is not None:
        customer_repository = PostgresCustomerRepository(database_engine)
        order_store: InMemoryOrderStore | PostgresOrderStore = PostgresOrderStore(database_engine)
    else:
        customer_repository = InMemoryCustomerRepository(seed_customers())
        shared_lock = RLock()
        memory_order_store = InMemoryOrderStore(customer_repository, lock=shared_lock)
        memory_order_store.replace_all(
            seed_products(),
            seed_orders(),
            quantize_money(settings.default_tax_rate),
        )
        order_store = memory_order_store
    customers = CustomerService(customer_repository, application_clock)
    orders = OrderService(order_store, application_clock, customer_repository)

    app = FastAPI(title="LabApp API", dependencies=[Depends(origin_guard)])
    app.state.settings = settings
    app.state.engine = database_engine
    app.state.container = container
    app.state.customer_repository = customer_repository
    app.state.customers = customers
    app.state.order_store = order_store
    app.state.orders = orders
    app.state.clock_store = clock_store
    app.state.fault_store = fault_store
    # add_middleware wraps the existing app, so the last one added is the outermost.
    # Outside to inside: request id, rate limit, controls guard, request controls,
    # body size, application.
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestControlsMiddleware, settings=settings, controls=request_controls)
    app.add_middleware(ControlsGuardMiddleware, settings=settings)
    app.add_middleware(RateLimitMiddleware, container=container)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(customers_router)
    app.include_router(orders_router)
    payment_gateway = FakeGateway()
    faulty_gateway = FaultyGateway(payment_gateway, fault_store, enabled=controls_enabled)
    invoice_store: InMemoryInvoiceStore | PostgresInvoiceStore
    if database_engine is None:
        invoice_store = InMemoryInvoiceStore(
            order_store,
            customer_repository,
            faulty_gateway,
            lock=shared_lock,
        )
        invoice_store.replace_all(seed_invoices(), seed_payments())
        memory_order_store.invoices = invoice_store
    else:
        invoice_store = PostgresInvoiceStore(database_engine, faulty_gateway)
    invoices = InvoiceService(
        invoice_store,
        order_store,
        customer_repository,
        application_clock,
        LoggingMailer(),
        settings.session_secret.encode(),
    )
    app.state.invoice_store = invoice_store
    app.state.payment_gateway = payment_gateway
    app.state.invoices = invoices
    if database_engine is None:
        resetter: MemoryResetter | PostgresResetter = MemoryResetter(
            customers=customer_repository,
            orders=memory_order_store,
            invoices=invoice_store,
            clock_store=clock_store,
            fault_store=fault_store,
            default_tax_rate=settings.default_tax_rate,
            reset_limiters=container.reset_limiters,
        )
    else:
        resetter = PostgresResetter(
            database_engine,
            customers=customer_repository,
            orders=order_store,
            invoices=invoice_store,
            default_tax_rate=settings.default_tax_rate,
            reset_limiters=container.reset_limiters,
        )
    app.state.resetter = resetter
    app.include_router(invoices_router)
    app.include_router(testcontrols_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
