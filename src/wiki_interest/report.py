"""Series-input contract for the report command.

Charts and PDFs are not implemented yet.
"""

from __future__ import annotations

from typing import Any

from wiki_interest import ContractError
from wiki_interest.resolve import language_code, validate_date_range

_ITEM_KEYS = {"lang", "title", "start", "end"}


def validate_series_input(data: object) -> dict[str, Any]:
    """Validate an explicit list of series. Does not expand combinations."""
    payload = _object(data, "series input")
    if set(payload) != {"series"}:
        raise ContractError("series input keys must be ['series']")
    series = payload["series"]
    if not isinstance(series, list) or not series:
        raise ContractError("series must be a non-empty list")
    return {"series": [_item(item, index) for index, item in enumerate(series)]}


def _item(data: object, index: int) -> dict[str, str]:
    field = f"series[{index}]"
    item = _object(data, field)
    if set(item) != _ITEM_KEYS:
        raise ContractError(f"{field} keys must be lang, title, start, and end")
    validate_date_range(item["start"], item["end"])
    title = item["title"]
    if not isinstance(title, str) or not title.strip():
        raise ContractError(f"{field}.title must be a non-empty string")
    return {
        "lang": language_code(item["lang"], f"{field}.lang"),
        "title": title,
        "start": item["start"],
        "end": item["end"],
    }


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value
