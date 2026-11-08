"""The error codes of docs/SPEC.md and the ones in the application code."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

from . import support

CODE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]*")

# Codes that the document defines but the application never raises. The list is
# empty today: every code in an error table is a string literal in backend/app/.
DOCUMENT_ONLY_CODES: frozenset[str] = frozenset()


def _python_files() -> list[Path]:
    return sorted(support.APP_ROOT.rglob("*.py"))


def _call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _docstring_values(tree: ast.AST) -> set[int]:
    values: set[int] = set()
    definitions = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if not isinstance(node, definitions):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            values.add(id(first.value))
    return values


def application_string_literals() -> set[str]:
    """Every string literal in backend/app/, except docstrings."""
    literals: set[str] = set()
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        docstrings = _docstring_values(tree)
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in docstrings
            ):
                literals.add(node.value)
    return literals


def _code_argument(call: ast.Call) -> ast.expr | None:
    if len(call.args) > 1:
        return call.args[1]
    for keyword in call.keywords:
        if keyword.arg == "code":
            return keyword.value
    return None


def _module_code_constants(tree: ast.AST) -> Iterator[str]:
    for node in tree.body:  # type: ignore[attr-defined]
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        else:
            continue
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Constant):
            continue
        if not isinstance(value.value, str):
            continue
        if CODE_PATTERN.fullmatch(target.id) and CODE_PATTERN.fullmatch(value.value):
            yield value.value


def application_raised_codes() -> set[str]:
    """Codes the application builds: ApiError literals and code constants."""
    codes: set[str] = set()
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func) not in {"ApiError", "problem_response"}:
                continue
            code = _code_argument(node)
            if isinstance(code, ast.Constant) and isinstance(code.value, str):
                codes.add(code.value)
        codes.update(_module_code_constants(tree))
    return codes


def document_codes() -> set[str]:
    return {row["Code"] for row in support.spec_error_rows()}


def test_every_document_error_table_only_has_code_shaped_rows() -> None:
    for row in support.spec_error_rows():
        assert CODE_PATTERN.fullmatch(row["Code"]), row


def test_every_document_code_appears_in_the_application_code() -> None:
    document = document_codes()
    literals = application_string_literals()

    missing = sorted(document - literals - DOCUMENT_ONLY_CODES)

    assert not missing, f"codes in the SPEC but not in backend/app: {missing}"


def test_the_document_only_codes_are_explained_and_still_in_the_document() -> None:
    assert DOCUMENT_ONLY_CODES <= document_codes()


def test_every_code_the_application_raises_appears_in_the_document() -> None:
    raised = application_raised_codes()
    document = document_codes()

    missing = sorted(raised - document)

    assert raised, "the source scan found no error codes at all"
    assert not missing, f"codes in backend/app but not in the SPEC: {missing}"
