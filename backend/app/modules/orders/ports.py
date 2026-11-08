"""Storage port for orders, products and settings."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from app.domain.orders import OrderAction, OrderStatus
from app.domain.sorting import SortSpec
from app.modules.orders.models import Order, Product


class OrderNotFound(Exception):
    """The requested order does not exist."""


class LineNotFound(Exception):
    """The requested line does not belong to the order."""


class ProductNotFound(Exception):
    """The requested product does not exist."""


class CustomerNotFound(Exception):
    """The requested customer does not exist."""


class VersionConflict(Exception):
    """The stored version differs from the expected version."""


class OrderNotEditable(Exception):
    """The order is not a draft."""


class CustomerInactive(Exception):
    """A customer that the operation needs is inactive."""


class OrderStore(Protocol):
    """Storage for products, the tax rate and orders.

    Order mutations are atomic. A SQL implementation locks the order row first
    (``SELECT ... FOR UPDATE``), then the customer row (``FOR SHARE``), then every
    affected product row in ascending id order. The version and the state are checked
    after locking. The domain functions in ``app.domain.orders`` raise ``ApiError`` for
    business rule failures; the store calls them at the documented point and lets the
    error propagate unchanged.
    """

    def list_products(self, *, sort: SortSpec | None = None) -> list[Product]:
        """Return every product following ``sort`` (ordered by id when absent).

        Ties are broken by id in the same direction.
        """
        ...

    def get_product(self, id: int) -> Product | None:
        """Return one product, or ``None``."""
        ...

    def get_tax_rate(self) -> Decimal:
        """Return the current tax rate, with two decimals."""
        ...

    def set_tax_rate(self, rate: Decimal) -> None:
        """Store the current tax rate.

        The value is already validated and has two decimals; it does not change
        confirmed or cancelled orders.
        """
        ...

    def list_orders(
        self,
        *,
        query: str | None,
        status: OrderStatus | None,
        customer_id: int | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[tuple[Order, str]], int]:
        """Return one page of orders and the total number of matches.

        Each item is the order together with the **current** name of its customer.
        Results follow ``sort`` (``created_at`` descending when it is absent),
        with ties broken by id in the same direction.
        ``query`` is already trimmed and non-empty when given. It is literal text
        (``%``, ``_`` and ``\\`` have no special meaning), matched as a contains
        against the order number or the customer's current name on the
        ``normalize_for_search`` form. This read takes no locks.
        """
        ...

    def get_order(self, id: int) -> Order | None:
        """Return one order, or ``None``. This read takes no locks."""
        ...

    def create_order(self, customer_id: int, now: datetime) -> Order:
        """Create and return a new draft.

        Locks the customer row ``FOR SHARE`` and checks that it exists and is active
        (``CustomerNotFound``, ``CustomerInactive``). Assigns the next ``PED`` number
        inside the same transaction. The order has no lines, status ``draft``,
        ``version`` 1 and no tax rate.
        """
        ...

    def set_customer(
        self,
        id: int,
        customer_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        """Change the customer of a draft.

        Locks the order row, then the new customer row ``FOR SHARE``. Checks, in this
        order: ``OrderNotFound``; the new customer exists (``CustomerNotFound``);
        ``VersionConflict``; ``OrderNotEditable``; the new customer is active
        (``CustomerInactive``). The old customer's status is irrelevant. Setting the
        same customer is a no-op that returns the stored order untouched. A real
        change increases ``version`` by 1 and sets ``updated_at``.
        """
        ...

    def add_line(
        self,
        id: int,
        product_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        """Add a line to a draft.

        Locks the order row, then the current customer row ``FOR SHARE``, then the
        product row. Checks, in this order: ``OrderNotFound``; the product exists
        (``ProductNotFound``); ``VersionConflict``; ``OrderNotEditable``; the current
        customer is active (``CustomerInactive``). Then it calls
        ``validate_draft_lines`` on the candidate list, which raises
        ``ORDER_DUPLICATE_PRODUCT`` or ``ORDER_TOO_MANY_LINES``. The line copies the
        product's SKU, name and price and receives the next line id. A real change
        increases ``version`` by 1 and sets ``updated_at``.
        """
        ...

    def set_quantity(
        self,
        id: int,
        line_id: int,
        quantity: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        """Change a line quantity of a draft.

        Locks the order row, then the current customer row ``FOR SHARE``. Checks, in
        this order: ``OrderNotFound``; the line belongs to the order
        (``LineNotFound``); ``VersionConflict``; ``OrderNotEditable``; the current
        customer is active (``CustomerInactive``). The unit price is preserved. The
        same quantity is a no-op that returns the stored order untouched. A real
        change increases ``version`` by 1 and sets ``updated_at``.
        """
        ...

    def remove_line(
        self,
        id: int,
        line_id: int,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        """Remove a line from a draft.

        Locks the order row, then the current customer row ``FOR SHARE``. Checks, in
        this order: ``OrderNotFound``; the line belongs to the order
        (``LineNotFound``); ``VersionConflict``; ``OrderNotEditable``; the current
        customer is active (``CustomerInactive``). A successful removal increases
        ``version`` by 1 and sets ``updated_at``.
        """
        ...

    def transition(
        self,
        id: int,
        action: OrderAction,
        expected_version: int | None,
        now: datetime,
    ) -> Order:
        """Apply one transition to an order.

        Locks the order row first. Checks, in this order: ``OrderNotFound``;
        ``VersionConflict``; the transition is allowed, through ``next_status``
        (``INVALID_TRANSITION``). For confirm it then checks the current customer is
        active (``CustomerInactive``), calls ``ensure_confirmable`` and
        ``check_stock`` (which raises ``INSUFFICIENT_STOCK`` with every shortage
        ordered by product id), and only after that decrements the stock of every
        line, stores the current tax rate and moves to ``confirmed``. Cancelling a
        confirmed order returns every line's stock; cancelling a draft changes no
        stock. Both cancels store the current tax rate. Shipping moves ``paid`` to
        ``shipped``. Every real transition increases ``version`` by 1 and sets
        ``updated_at``. A SQL implementation locks the customer ``FOR SHARE`` for
        confirm and the affected product rows in ascending id order.
        """
        ...

    def replace_all(
        self,
        products: Iterable[Product],
        orders: Iterable[Order],
        tax_rate: Decimal,
    ) -> None:
        """Replace the catalog, the orders and the tax rate in one transaction.

        The next order id and the next ``PED`` number continue after the highest
        existing ones; the next line id continues after the highest existing line
        id. Empty content starts both sequences at 1.
        """
        ...

    def attach_invoice(self, order_id: int, invoice_id: int, now: datetime) -> Order:
        """Link an invoice to its order.

        Called only by ``issue_invoice``. Checks ``OrderNotFound``, sets
        ``invoice_id``, increases ``version`` by 1 and sets ``updated_at`` to
        ``now``.
        """
        ...

    def mark_paid(self, order_id: int, now: datetime) -> Order:
        """Move a confirmed order to ``paid``.

        Checks ``OrderNotFound`` and the transition; another state raises
        ``INVALID_TRANSITION``. Increases ``version`` by 1 and sets
        ``updated_at`` to ``now``.
        """
        ...

    def link_invoices(self, links: Mapping[int, int]) -> None:
        """Set the ``invoice_id`` of every order from ``links``.

        Every order gets ``links.get(order_id)``, so an order absent from the
        mapping is left with no invoice. It never changes ``version`` or
        ``updated_at``. Used only by the seed and by ``replace_all``, because the
        seeded orders must keep version 1 and ``updated_at == created_at``.
        """
        ...
