"""Customer service: validation, listing and port error translation."""

from __future__ import annotations

from collections.abc import Mapping

from app.errors import ERROR_MESSAGES, NOT_FOUND, ApiError
from app.infra.clock import Clock
from app.modules.customers.models import Changes, Customer, CustomerStatus
from app.modules.customers.ports import (
    CustomerNotFound,
    CustomerRepository,
    EmailTaken,
    VersionConflict,
)
from app.modules.customers.validation import (
    VALIDATION_DETAIL,
    has_control_character,
    validate_changes,
    validate_new,
)

PAGE_SIZE = 20
MAX_PAGE = 1_000_000
MAX_ID = 2_147_483_647
MAX_QUERY_LENGTH = 100

VERSION_CONFLICT_MESSAGE = "El registro cambió mientras lo editabas. Recarga e inténtalo de nuevo."
EMAIL_TAKEN_MESSAGE = "Ya existe un cliente con ese email."


def _error(field: str, code: str, message: str) -> dict[str, str]:
    return {"field": field, "code": code, "message": message}


def _raise_validation(errors: list[dict[str, str]]) -> None:
    raise ApiError(422, "VALIDATION_ERROR", VALIDATION_DETAIL, errors=errors)


def _not_found() -> ApiError:
    return ApiError(404, NOT_FOUND, ERROR_MESSAGES[NOT_FOUND])


def _version_out_of_range() -> dict[str, str]:
    return _error(
        "version",
        "OUT_OF_RANGE",
        f"El valor debe estar entre 1 y {MAX_ID}.",
    )


class CustomerService:
    """Customer business operations over the repository port."""

    def __init__(self, repository: CustomerRepository, clock: Clock) -> None:
        self._repository = repository
        self._clock = clock

    def list_customers(
        self,
        page: int,
        query: str | None,
        status: CustomerStatus | None,
    ) -> tuple[list[Customer], int]:
        """Validate the list parameters and return one page plus its total."""
        errors: list[dict[str, str]] = []
        if not 1 <= page <= MAX_PAGE:
            errors.append(
                _error(
                    "page",
                    "OUT_OF_RANGE",
                    "El valor debe estar entre 1 y 1000000.",
                )
            )

        normalized_query: str | None = None
        if query is not None:
            if has_control_character(query):
                errors.append(_error("q", "INVALID_FORMAT", "El formato no es válido."))
            else:
                trimmed = query.strip()
                if trimmed:
                    if len(trimmed) > MAX_QUERY_LENGTH:
                        errors.append(
                            _error(
                                "q",
                                "TOO_LONG",
                                "Debe tener como máximo 100 caracteres.",
                            )
                        )
                    else:
                        normalized_query = trimmed

        if errors:
            _raise_validation(errors)

        return self._repository.list(
            query=normalized_query,
            status=status,
            page=page,
            page_size=PAGE_SIZE,
        )

    def get(self, id: int) -> Customer:
        """Return one customer or raise the 404 problem."""
        if not 1 <= id <= MAX_ID:
            raise _not_found()
        customer = self._repository.get(id)
        if customer is None:
            raise _not_found()
        return customer

    def create(self, data: Mapping[str, object | None]) -> Customer:
        """Validate and create a customer."""
        new_customer = validate_new(data)
        try:
            return self._repository.add(new_customer, self._clock.now())
        except EmailTaken as error:
            raise ApiError(409, "CUSTOMER_EMAIL_TAKEN", EMAIL_TAKEN_MESSAGE) from error

    def update(
        self,
        customer_id: int,
        data: Mapping[str, object | None],
        version: int,
    ) -> Customer:
        """Validate and update a customer."""
        if not 1 <= version <= MAX_ID:
            _raise_validation([_version_out_of_range()])
        if not 1 <= customer_id <= MAX_ID:
            raise _not_found()

        changes: Changes = validate_changes(data)
        try:
            return self._repository.update(
                customer_id,
                changes,
                expected_version=version,
                now=self._clock.now(),
            )
        except CustomerNotFound as error:
            raise _not_found() from error
        except VersionConflict as error:
            raise ApiError(409, "VERSION_CONFLICT", VERSION_CONFLICT_MESSAGE) from error
        except EmailTaken as error:
            raise ApiError(409, "CUSTOMER_EMAIL_TAKEN", EMAIL_TAKEN_MESSAGE) from error

    def deactivate(self, customer_id: int, expected_version: int | None) -> Customer:
        """Set a customer to inactive."""
        return self._set_status(customer_id, CustomerStatus.INACTIVE, expected_version)

    def reactivate(self, customer_id: int, expected_version: int | None) -> Customer:
        """Set a customer to active."""
        return self._set_status(customer_id, CustomerStatus.ACTIVE, expected_version)

    def _set_status(
        self,
        customer_id: int,
        status: CustomerStatus,
        expected_version: int | None,
    ) -> Customer:
        if not 1 <= customer_id <= MAX_ID:
            raise _not_found()
        try:
            return self._repository.set_status(
                customer_id,
                status,
                expected_version,
                self._clock.now(),
            )
        except CustomerNotFound as error:
            raise _not_found() from error
        except VersionConflict as error:
            raise ApiError(409, "VERSION_CONFLICT", VERSION_CONFLICT_MESSAGE) from error
