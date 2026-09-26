"""Series-input contract and report orchestration.

``report`` fetches pageviews, calculates metrics into ``analysis.json``, then
draws ``chart.png`` and a one-page ``report.pdf`` from that file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from wiki_interest import ContractError
from wiki_interest.analyze import build_analysis, write_analysis_data
from wiki_interest.http import GetJson
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


def run_report(
    series_input: object,
    out_dir: str,
    *,
    fetch: GetJson | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Path:
    """Fetch pageviews and write pageviews.json, analysis.json, chart.png, and report.pdf.

    The chart and PDF are rendered from the written analysis.json. They do not
    recalculate metrics.
    """
    # Imported here so pageviews can keep importing validate_series_input.
    from wiki_interest.chart import write_chart
    from wiki_interest.pageviews import fetch_pageviews, write_pageviews_data
    from wiki_interest.pdf_report import write_pdf

    pageviews = fetch_pageviews(series_input, fetch=fetch, sleep=sleep)
    analysis = build_analysis(pageviews)
    write_pageviews_data(pageviews, out_dir)
    path = write_analysis_data(analysis, out_dir)
    stored = json.loads(path.read_text(encoding="utf-8"))
    chart_path = write_chart(stored, out_dir)
    write_pdf(stored, out_dir, chart_path)
    return path


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
