"""Normalization used by customer search."""

from __future__ import annotations

import unicodedata


def normalize_for_search(text: str) -> str:
    """Remove accents and case so search is literal but accent-insensitive."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return without_marks.casefold()
