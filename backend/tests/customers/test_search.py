"""Tests for customer search normalization."""

from __future__ import annotations

from app.modules.customers.search import normalize_for_search


def test_normalize_for_search_ignores_case_and_accents() -> None:
    assert normalize_for_search("Cafetería") == "cafeteria"
    assert normalize_for_search("ÉPSILON") == "epsilon"
    assert normalize_for_search("  Café\tCon Leche  ") == "  cafe\tcon leche  "


def test_normalize_for_search_handles_other_unicode_cases() -> None:
    assert normalize_for_search("Straße") == "strasse"
    assert normalize_for_search("İstanbul") == "istanbul"
