"""Storage port for invoices, payments and idempotency keys."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Protocol

from app.domain.sorting import SortSpec
from app.modules.invoices.models import (
    Invoice,
    InvoiceStatus,
    Payment,
    PaymentAttempt,
    PaymentOutcome,
    StoredKey,
    StoredResponse,
)


class InvoiceNotFound(Exception):
    """The requested invoice does not exist."""


class InvoiceStore(Protocol):
    """Storage for invoices, payments and idempotency keys.

    Every operation is atomic. A SQL implementation uses one transaction per
    method and locks the order row first (``FOR UPDATE``), then the invoice row
    (``FOR NO KEY UPDATE``) and then the customer row (``FOR SHARE``) when it is
    needed. The version and the state are checked after locking. The domain
    ``ApiError``s of ``app.modules.invoices.rules`` propagate unchanged.
    """

    def list_invoices(
        self,
        *,
        query: str | None,
        status: InvoiceStatus | None,
        order_id: int | None,
        page: int,
        page_size: int,
        sort: SortSpec | None = None,
    ) -> tuple[list[Invoice], int]:
        """Return one page of invoices and the total number of matches.

        Results follow ``sort`` (``created_at`` descending when it is absent),
        with ties broken by id in the same direction.
        ``query`` is already trimmed and non-empty when given. It is literal text
        (``%``, ``_`` and ``\\`` have no special meaning), matched as a contains
        against the invoice number or the customer name stored in the snapshot.
        The returned invoices may have empty ``lines`` and ``payments``. This read
        takes no locks.
        """
        ...

    def get_invoice(self, id: int) -> Invoice | None:
        """Return one invoice with its lines and its payments ordered by id.

        This read takes no locks.
        """
        ...

    def find_key(self, invoice_id: int, key: str, now: datetime) -> StoredKey | None:
        """Return a committed, not expired key of this invoice, or ``None``.

        Keys live for 24 hours, measured with the application clock. This is a
        plain read used for the early replay decision, before the request body is
        validated.
        """
        ...

    def issue_invoice(
        self,
        order_id: int,
        expected_order_version: int | None,
        now: datetime,
    ) -> Invoice:
        """Issue the invoice of a confirmed order in one atomic step.

        Locks the order row and then the customer row ``FOR SHARE``. Checks, in
        this order: the order exists (``OrderNotFound``); the version
        (``VersionConflict``); ``INVOICE_ALREADY_EXISTS``; ``ORDER_NOT_INVOICEABLE``;
        ``CUSTOMER_TAX_ID_REQUIRED``. Takes the next ``FAC`` number, copies the
        order line and customer snapshots, stores the invoice with status
        ``issued`` and version 1, and gives the order its ``invoice_id`` while
        increasing its version by 1 and setting its ``updated_at``. The customer
        may be inactive: an inactive customer's confirmed order can still be
        invoiced.
        """
        ...

    def register_payment(
        self,
        invoice_id: int,
        *,
        key: str,
        fingerprint: str,
        expected_version: int | None,
        attempt: PaymentAttempt,
        respond: Callable[[Payment, Invoice], StoredResponse],
        now: datetime,
    ) -> PaymentOutcome:
        """Register one payment attempt atomically and idempotently.

        Locks the order row first, then the invoice row. Inside the lock it
        looks the key up (scoped to the invoice, remembered 24 hours): the same
        fingerprint replays the stored response and reports ``replayed=True``;
        another fingerprint raises ``IDEMPOTENCY_KEY_REUSED``. Otherwise it
        checks, in this order, the stale version (``VersionConflict``),
        ``INVOICE_NOT_PAYABLE`` and ``PAYMENT_AMOUNT_MISMATCH``, then calls the
        gateway while the locks are held, stores the payment row (``approved``,
        ``declined`` or ``failed``), and when approved sets the invoice to
        ``paid`` (version + 1) and calls the order's ``mark_paid``. It then reads
        the invoice again with its lines and payments and calls
        ``respond(payment, invoice_after)``, storing its result with the key only
        when a payment row was created. A request rejected before the payment row
        is stored does not consume the key.

        In SQL the claim of the key is a unique ``(invoice_id, key)`` row
        inserted before the locks, so two concurrent requests with the same key
        give one payment and the second replays the first response.
        """
        ...

    def void_for_order(self, order_id: int, now: datetime) -> None:
        """Void the ``issued`` invoice of an order.

        Sets the status to ``void`` and increases the version by 1. Does nothing
        when the order has no invoice or when the invoice is already final.
        """
        ...

    def replace_all(
        self,
        invoices: Iterable[Invoice],
        payments: Iterable[Payment],
    ) -> None:
        """Replace the invoices, the payments and the idempotency keys.

        The next invoice id, invoice line id, ``FAC`` number and payment id
        continue after the highest given values; empty content starts them at 1.
        It also calls ``link_invoices`` on the order store so that every given
        invoice is linked to its order and no other order is, without changing
        the orders' version or ``updated_at``.
        """
        ...
