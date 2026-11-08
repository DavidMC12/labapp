"""Tests for importing customers from a CSV file."""

from __future__ import annotations

import inspect
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.modules.customers.ports import EmailTaken
from tests.customers.helpers import assert_problem

CSV = "text/csv"


def find_route(app: FastAPI, path: str, method: str) -> APIRoute:
    """Return an APIRoute, also when it lives inside an included router."""
    pending = list(app.routes)
    while pending:
        route = pending.pop()
        if isinstance(route, APIRoute):
            if route.path == path and method in route.methods:
                return route
            continue
        nested = getattr(getattr(route, "original_router", None), "routes", None)
        if nested:
            pending.extend(nested)
    raise AssertionError(f"{method} {path} is not an APIRoute")


def upload(
    client: TestClient,
    text: str,
    filename: str = "customers.csv",
) -> Any:
    return client.post(
        "/api/customers/import",
        files={"file": (filename, text.encode("utf-8"), CSV)},
    )


def upload_bytes(
    client: TestClient,
    content: bytes,
    filename: str = "customers.csv",
) -> Any:
    return client.post(
        "/api/customers/import",
        files={"file": (filename, content, CSV)},
    )


def import_error(response: Any, field: str, code: str, message: str) -> None:
    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert body["detail"] == "Revisa los datos ingresados."
    assert body["errors"] == [{"field": field, "code": code, "message": message}]


def test_the_import_route_is_synchronous(app: FastAPI) -> None:
    # The service reaches the database synchronously and may wait on locks. An async
    # route would block the event loop meanwhile, stalling health and every other
    # request of the instance; a plain ``def`` route runs in FastAPI's thread pool.
    route = find_route(app, "/api/customers/import", "POST")

    assert inspect.iscoroutinefunction(route.endpoint) is False


def test_imports_three_rows_in_file_order(
    clients: dict[str, TestClient],
) -> None:
    text = (
        "name,email,phone,tax_id,address\n"
        "Alpha,alpha@example.test,+1 555 01,ALPH-1,Calle 1\n"
        "Beta,beta2@example.test,,,\n"
        "Gamma,gamma2@example.test,,,\n"
    )

    response = upload(clients["sales"], text)

    assert response.status_code == 201
    assert response.headers["content-type"] == "application/json"
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["created"] == 3
    assert [item["id"] for item in body["items"]] == [11, 12, 13]
    assert [item["name"] for item in body["items"]] == ["Alpha", "Beta", "Gamma"]
    for item in body["items"]:
        assert item["status"] == "active"
        assert item["version"] == 1
        assert item["created_at"].endswith("Z")
        assert item["updated_at"] == item["created_at"]
    read = clients["sales"].get("/api/customers/13")
    assert read.status_code == 200
    assert read.json()["email"] == "gamma2@example.test"


def test_stores_an_empty_optional_value_as_null_and_normalizes_the_email(
    clients: dict[str, TestClient],
) -> None:
    text = "name,email,phone,tax_id,address\n  New Customer  ,  NEW@EXAMPLE.TEST  ,  ,  ,  \n"

    response = upload(clients["sales"], text)

    assert response.status_code == 201
    item = response.json()["items"][0]
    assert item["name"] == "New Customer"
    assert item["email"] == "new@example.test"
    assert item["phone"] is None
    assert item["tax_id"] is None
    assert item["address"] is None


def test_keeps_the_formula_quote_of_the_export(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email\n'=1+1,formula@example.test\n",
    )

    assert response.status_code == 201
    assert response.json()["items"][0]["name"] == "'=1+1"


def test_reports_every_row_error_in_file_order_and_creates_nothing(
    clients: dict[str, TestClient],
) -> None:
    before = clients["sales"].get("/api/customers").json()["total"]
    text = (
        "name,email,phone\n"
        "A,jane@example.test,+1 555 01\n"
        "Valid Name,not-an-email,\n"
        "Other Name,good@example.test,abc1234\n"
    )

    response = upload(clients["sales"], text)

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert [(error["field"], error["code"]) for error in body["errors"]] == [
        ("rows[2].name", "TOO_SHORT"),
        ("rows[3].email", "INVALID_FORMAT"),
        ("rows[4].phone", "INVALID_FORMAT"),
    ]
    assert clients["sales"].get("/api/customers").json()["total"] == before


def test_reports_a_name_above_the_maximum(clients: dict[str, TestClient]) -> None:
    response = upload(
        clients["sales"],
        f"name,email\n{'A' * 121},long@example.test\n",
    )

    import_error(
        response,
        "rows[2].name",
        "TOO_LONG",
        "Debe tener como máximo 120 caracteres.",
    )


def test_reports_an_email_that_the_seed_already_uses(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email\nNew Name,ACME@EXAMPLE.TEST\n",
    )

    import_error(
        response,
        "rows[2].email",
        "CUSTOMER_EMAIL_TAKEN",
        "Ya existe un cliente con ese email.",
    )


def test_reports_the_second_occurrence_of_an_email_of_the_file(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email\nFirst,repeat@example.test\nSecond,REPEAT@example.test\n",
    )

    import_error(
        response,
        "rows[3].email",
        "CUSTOMER_EMAIL_TAKEN",
        "Ya existe un cliente con ese email.",
    )


def test_reports_a_row_with_fewer_cells_than_the_header(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email,phone,address\n"
        "One,one@example.test,+1 555 01,Calle 1\n"
        "Two,two@example.test,+1 555 02,Calle 2\n"
        "Three,three@example.test\n",
    )

    import_error(response, "rows[4]", "INVALID_FORMAT", "El formato no es válido.")


def test_reports_a_row_with_more_cells_than_the_header(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email\nOne,one@example.test,extra\n",
    )

    import_error(response, "rows[2]", "INVALID_FORMAT", "El formato no es válido.")


def test_caps_the_error_list_at_one_hundred_entries(
    clients: dict[str, TestClient],
) -> None:
    rows = [f"A,bad{index}@example.test" for index in range(150)]
    text = "name,email\n" + "\n".join(rows) + "\n"

    response = upload(clients["sales"], text)

    body = assert_problem(response, 422, "VALIDATION_ERROR")
    assert len(body["errors"]) == 100
    assert body["errors"][0]["field"] == "rows[2].name"
    assert body["errors"][-1]["field"] == "rows[101].name"


def test_an_empty_file_is_required(clients: dict[str, TestClient]) -> None:
    response = upload_bytes(clients["sales"], b"")

    import_error(response, "file", "REQUIRED", "Este campo es obligatorio.")


def test_a_file_with_only_the_header_is_out_of_range(
    clients: dict[str, TestClient],
) -> None:
    response = upload(clients["sales"], "name,email\n")

    import_error(response, "file", "OUT_OF_RANGE", "El valor debe estar entre 1 y 200.")


def test_two_hundred_and_one_rows_are_out_of_range(
    clients: dict[str, TestClient],
) -> None:
    rows = [f"Customer {index},c{index}@example.test" for index in range(201)]
    response = upload(clients["sales"], "name,email\n" + "\n".join(rows) + "\n")

    import_error(response, "file", "OUT_OF_RANGE", "El valor debe estar entre 1 y 200.")


def test_a_file_without_the_csv_extension_is_invalid(
    clients: dict[str, TestClient],
) -> None:
    response = upload(
        clients["sales"],
        "name,email\nOne,one@example.test\n",
        filename="customers.txt",
    )

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")


@pytest.mark.parametrize(
    "header",
    ["name,email,status", "name,email,name", "name,phone"],
    ids=["unknown-column", "duplicated-column", "missing-email"],
)
def test_an_invalid_header_is_invalid(
    clients: dict[str, TestClient],
    header: str,
) -> None:
    response = upload(clients["sales"], f"{header}\nOne,one@example.test\n")

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")


def test_invalid_utf8_is_invalid(clients: dict[str, TestClient]) -> None:
    response = upload_bytes(
        clients["sales"],
        b"name,email\nOne\xff,one@example.test\n",
    )

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")


@pytest.mark.parametrize(
    "text",
    [
        'name,email,address\nAna,a@x.co,"Calle 1\nBeto,b@x.co,Calle 2\n',
        'name,email,address\nAna,"Calle 1,a@x.co,Calle 2\nBeto,b@x.co,Calle 2\n',
        'name,email,address\nAna,a@x.co,Calle 1\nBeto,b@x.co,"',
    ],
    ids=["last-column", "middle-column", "start-of-field-at-the-end"],
)
def test_an_unclosed_quote_rejects_the_whole_file(
    clients: dict[str, TestClient],
    text: str,
) -> None:
    before = clients["sales"].get("/api/customers").json()["total"]

    response = upload(clients["sales"], text)

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")
    assert clients["sales"].get("/api/customers").json()["total"] == before


def test_a_quote_after_the_closing_quote_rejects_the_whole_file(
    clients: dict[str, TestClient],
) -> None:
    before = clients["sales"].get("/api/customers").json()["total"]

    response = upload(clients["sales"], 'name,email\n"a"b,ab@example.test\n')

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")
    assert clients["sales"].get("/api/customers").json()["total"] == before


def test_a_bare_quote_inside_an_unquoted_field_is_stored(
    clients: dict[str, TestClient],
) -> None:
    response = upload(clients["sales"], 'name,email\n5" pipe,pipe@example.test\n')

    assert response.status_code == 201
    assert response.json()["items"][0]["name"] == '5" pipe'


def test_a_malformed_multipart_body_is_the_framework_400(
    clients: dict[str, TestClient],
) -> None:
    # A body whose boundary does not match the header is rejected by FastAPI
    # before the route runs: it does not carry the JSON error code.
    response = clients["sales"].post(
        "/api/customers/import",
        content=(
            b'--nope\r\nContent-Disposition: form-data; name="file"; filename="a.csv"'
            b"\r\n\r\nname,email\r\nOne,one@example.test\r\n--nope--\r\n"
        ),
        headers={"Content-Type": "multipart/form-data; boundary=other"},
    )

    body = assert_problem(response, 400, "BAD_REQUEST")
    assert body["detail"] == "No se pudo completar la solicitud."


def test_a_missing_file_part_is_required(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post(
        "/api/customers/import",
        data={"other": "value"},
    )

    import_error(response, "file", "REQUIRED", "Este campo es obligatorio.")


def test_a_plain_form_field_named_file_is_invalid(clients: dict[str, TestClient]) -> None:
    # A part without a filename is a plain field, not a file: FastAPI rejects it
    # and the route answers the field error instead of crashing.
    response = clients["sales"].post(
        "/api/customers/import",
        data={"file": "not a file"},
    )

    import_error(response, "file", "INVALID_FORMAT", "El formato no es válido.")


def test_two_file_parts_use_the_last_one(clients: dict[str, TestClient]) -> None:
    response = clients["sales"].post(
        "/api/customers/import",
        files=[
            ("file", ("a.csv", b"name,email\nOne,one@example.test\n", CSV)),
            ("file", ("b.csv", b"name,email\nTwo,two@example.test\n", CSV)),
        ],
    )

    assert response.status_code == 201
    assert [item["name"] for item in response.json()["items"]] == ["Two"]


def test_an_empty_filename_is_required(clients: dict[str, TestClient]) -> None:
    # What a browser sends for an empty file input: no name and no content.
    response = clients["sales"].post(
        "/api/customers/import",
        files={"file": ("", b"", CSV)},
    )

    import_error(response, "file", "REQUIRED", "Este campo es obligatorio.")


def test_a_lone_carriage_return_is_a_line_end(clients: dict[str, TestClient]) -> None:
    response = upload_bytes(
        clients["sales"],
        b"name,email\rOne,one@example.test\r",
    )

    assert response.status_code == 201
    assert [item["name"] for item in response.json()["items"]] == ["One"]


def test_a_nul_byte_in_a_value_is_invalid(clients: dict[str, TestClient]) -> None:
    response = upload_bytes(
        clients["sales"],
        b"name,email\nA\x00na,ana@example.test\n",
    )

    import_error(response, "rows[2].name", "INVALID_FORMAT", "El formato no es válido.")


def test_a_byte_order_mark_in_the_middle_is_part_of_the_value(
    clients: dict[str, TestClient],
) -> None:
    # Only a leading byte order mark is stripped; U+FEFF elsewhere is a format
    # character, not a control character, so it stays in the value.
    response = upload_bytes(
        clients["sales"],
        b"name,email\nAna,a@example.test\n\xef\xbb\xbfBeto,b@example.test\n",
    )

    assert response.status_code == 201
    assert [item["name"] for item in response.json()["items"]] == ["Ana", "\ufeffBeto"]


def test_a_record_with_twenty_thousand_cells_is_a_row_error(
    clients: dict[str, TestClient],
) -> None:
    row = ",".join(["x"] * 20_000)
    response = upload(clients["sales"], f"name,email\n{row}\n")

    import_error(response, "rows[2]", "INVALID_FORMAT", "El formato no es válido.")


def test_two_hundred_rows_of_the_longest_values_exceed_the_body_limit(
    clients: dict[str, TestClient],
) -> None:
    # About 200 short rows are far below the 100 KB limit, but the longest value
    # of every column crosses it: the body guard answers 413 before parsing.
    name = "N" * 120
    email = "e" * 240 + "@example.test"
    phone = "+1 555 01"
    tax_id = "T" * 30
    address = "A" * 200
    rows = [f"{name},{email},{phone},{tax_id},{address}" for _ in range(200)]
    text = "name,email,phone,tax_id,address\n" + "\n".join(rows) + "\n"
    assert len(text.encode("utf-8")) > 100 * 1024

    response = upload(clients["sales"], text)

    assert_problem(response, 413, "PAYLOAD_TOO_LARGE")


def test_a_part_with_another_name_is_ignored(
    clients: dict[str, TestClient],
) -> None:
    response = clients["sales"].post(
        "/api/customers/import",
        files={
            "file": ("customers.csv", b"name,email\nOne,one@example.test\n", CSV),
            "other": ("other.csv", b"name,email\nTwo,two@example.test\n", CSV),
        },
    )

    assert response.status_code == 201
    assert response.json()["created"] == 1


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_admin_and_sales_can_import(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = upload(
        clients[role],
        "name,email\nOne,one@example.test\n",
    )

    assert response.status_code == 201


@pytest.mark.parametrize("role", ["finance", "readonly"])
def test_roles_without_customer_management_cannot_import(
    clients: dict[str, TestClient],
    role: str,
) -> None:
    response = upload(
        clients[role],
        "name,email\nOne,one@example.test\n",
    )

    body = assert_problem(response, 403, "FORBIDDEN")
    assert body["detail"] == "No tienes permiso para realizar esta acción."


def test_permission_is_checked_before_the_file(
    clients: dict[str, TestClient],
) -> None:
    response = upload(clients["finance"], "not a csv")

    assert_problem(response, 403, "FORBIDDEN")


def test_import_without_a_session_is_unauthenticated(app: FastAPI) -> None:
    client = TestClient(app)

    response = upload(client, "name,email\nOne,one@example.test\n")

    body = assert_problem(response, 401, "UNAUTHENTICATED")
    assert body["detail"] == "Inicia sesión para continuar."


def test_a_file_above_the_body_limit_is_rejected(
    clients: dict[str, TestClient],
) -> None:
    response = upload_bytes(clients["sales"], b"x" * (120 * 1024))

    assert_problem(response, 413, "PAYLOAD_TOO_LARGE")


def test_an_email_taken_between_validation_and_insert_is_a_conflict(
    app: FastAPI,
    clients: dict[str, TestClient],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = app.state.customer_repository
    monkeypatch.setattr(repository, "existing_emails", lambda emails: set())

    def add_many(customers: Any, now: Any) -> Any:
        raise EmailTaken

    monkeypatch.setattr(repository, "add_many", add_many)

    response = upload(
        clients["sales"],
        "name,email\nOne,one@example.test\n",
    )

    body = assert_problem(response, 409, "CUSTOMER_EMAIL_TAKEN")
    assert body["detail"] == "Ya existe un cliente con ese email."
