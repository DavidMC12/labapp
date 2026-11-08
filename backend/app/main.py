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
from app.infra.clock import OffsetClock, SystemClock
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
from app.modules.invoices.gateway import FakeGateway
from app.modules.invoices.mail import LoggingMailer
from app.modules.invoices.routes import router as invoices_router
from app.modules.invoices.seed import seed_invoices, seed_payments
from app.modules.invoices.service import InvoiceService
from app.modules.orders.adapters.memory import InMemoryOrderStore
from app.modules.orders.adapters.postgres import PostgresOrderStore
from app.modules.orders.routes import router as orders_router
from app.modules.orders.seed import seed_orders, seed_products
from app.modules.orders.service import OrderService

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

    application_clock = clock if clock is not None else OffsetClock(SystemClock())
    database_engine = create_db_engine(settings) if settings.database_url is not None else None
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
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(ControlsGuardMiddleware, settings=settings)
    app.add_middleware(RateLimitMiddleware, container=container)
    app.add_middleware(RequestIdMiddleware)
    register_error_handlers(app)
    app.include_router(auth_router)
    app.include_router(customers_router)
    app.include_router(orders_router)
    payment_gateway = FakeGateway()
    invoice_store: InMemoryInvoiceStore | PostgresInvoiceStore
    if database_engine is None:
        invoice_store = InMemoryInvoiceStore(
            order_store,
            customer_repository,
            payment_gateway,
            lock=shared_lock,
        )
        invoice_store.replace_all(seed_invoices(), seed_payments())
        memory_order_store.invoices = invoice_store
    else:
        invoice_store = PostgresInvoiceStore(database_engine, payment_gateway)
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
    app.include_router(invoices_router)

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
