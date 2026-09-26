"""Daily Wikimedia pageviews for an explicit series list.

This module fetches and classifies days. Metric calculations live in
``metrics.py``. Charts and PDFs are a later milestone. It does not resolve
titles and it does not fill failed requests with numbers.
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from wiki_interest.http import GetJson, HttpError, get_json
from wiki_interest.report import validate_series_input

PAGEVIEW_API = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
PAGEVIEWS_FILENAME = "pageviews.json"
PAGEVIEW_MAX_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 1.0

_STAMP = re.compile(r"^\d{8}00$")

# Wikimedia documents that a pageviews 404 may mean zero views or data not
# yet loaded. The API does not distinguish those cases. This MVP refuses to
# invent zeros and surfaces the ambiguity instead.
PAGEVIEW_404_MESSAGE = (
    "pageview HTTP 404 is ambiguous: Wikimedia may mean zero pageviews or "
    "data not yet loaded, and the API does not distinguish them; refusing "
    "to invent values"
)


class PageviewError(RuntimeError):
    """Raised when a pageview series cannot be retrieved or parsed."""


def pageview_url(lang: str, title: str, start: date, end: date) -> str:
    """Build the per-article URL. The title is copied, not rewritten."""
    article = urllib.parse.quote(title.replace(" ", "_"), safe="")
    return (
        f"{PAGEVIEW_API}/{lang}.wikipedia/all-access/user/{article}/daily/"
        f"{start.strftime('%Y%m%d')}/{end.strftime('%Y%m%d')}"
    )


def parse_pageview_items(payload: object) -> dict[date, int]:
    """Read observed days from a pageview JSON object. Empty items are valid."""
    if not isinstance(payload, dict):
        raise PageviewError("pageview response must be an object")
    items = payload.get("items")
    if not isinstance(items, list):
        raise PageviewError("pageview response is missing items")
    counts: dict[date, int] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise PageviewError(f"pageview items[{index}] must be an object")
        stamp = item.get("timestamp")
        views = item.get("views")
        if not isinstance(stamp, str) or _STAMP.fullmatch(stamp) is None:
            raise PageviewError(f"pageview items[{index}] has an invalid timestamp")
        if isinstance(views, bool) or not isinstance(views, int) or views < 0:
            raise PageviewError(f"pageview items[{index}] views must be an integer >= 0")
        try:
            day = date(int(stamp[0:4]), int(stamp[4:6]), int(stamp[6:8]))
        except ValueError as exc:
            raise PageviewError(f"pageview items[{index}] has an invalid timestamp") from exc
        if day in counts:
            raise PageviewError(f"pageview response repeats {day.isoformat()}")
        counts[day] = views
    return counts


def classify_days(
    start: date,
    end: date,
    observed: dict[date, int],
    *,
    published_through: date | None = None,
) -> list[dict[str, Any]]:
    """Label every calendar day as observed, missing, or unavailable.

    A row with a number is observed. The API omits zeros and also omits days
    that are not published yet, and it does not say which is which.

    This is an implementation heuristic, not an API guarantee. Wikimedia says
    data is usually loaded within hours but delays can be 24 hours or more, so
    a fixed ``today - N days`` lag is not treated as an API rule.

    When the response contains at least one row, the latest returned timestamp
    is the published-through boundary unless ``published_through`` is passed
    explicitly. Omitted dates on or before that boundary are ``missing`` with
    views 0. Requested dates after that boundary are ``unavailable`` with
    views null.

    When the response contains no rows (HTTP 200 with empty ``items``), there
    is no returned boundary. The whole requested range is treated as
    ``missing`` with views 0, which is how this MVP records an all-zero
    published series. HTTP 404 is handled separately and never becomes zeros.
    """
    boundary = published_through
    if boundary is None and observed:
        boundary = max(observed)
    days: list[dict[str, Any]] = []
    current = start
    while current <= end:
        if current in observed:
            days.append(
                {"date": current.isoformat(), "views": observed[current], "status": "observed"}
            )
        elif boundary is not None and current > boundary:
            days.append({"date": current.isoformat(), "views": None, "status": "unavailable"})
        else:
            days.append({"date": current.isoformat(), "views": 0, "status": "missing"})
        current = date.fromordinal(current.toordinal() + 1)
    return days


def fetch_pageviews(
    series_input: object,
    *,
    fetch: GetJson | None = None,
    sleep: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Fetch each series in order. Does not expand topic, language, or period combinations."""
    validated = validate_series_input(series_input)
    client = fetch or get_json
    pause = sleep or time.sleep
    return {
        "series": [
            _fetch_one(item, fetch=client, sleep=pause) for item in validated["series"]
        ]
    }


def write_pageviews(
    series_input: object,
    out_dir: str,
    *,
    fetch: GetJson | None = None,
    sleep: Callable[[float], None] | None = None,
) -> Path:
    """Fetch every series, then write pageviews.json. Failures write no file."""
    payload = fetch_pageviews(series_input, fetch=fetch, sleep=sleep)
    return write_pageviews_data(payload, out_dir)


def write_pageviews_data(payload: dict[str, Any], out_dir: str) -> Path:
    """Write an already-fetched pageviews payload."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / PAGEVIEWS_FILENAME
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _fetch_one(
    item: dict[str, str],
    *,
    fetch: GetJson,
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    start = date.fromisoformat(item["start"])
    end = date.fromisoformat(item["end"])
    url = pageview_url(item["lang"], item["title"], start, end)
    label = f"{item['lang']}:{item['title']}"
    try:
        payload = _fetch_with_retries(url, fetch, sleep)
        counts = parse_pageview_items(payload)
    except PageviewError as exc:
        raise PageviewError(f"{label}: {exc}") from exc
    for day in counts:
        if day < start or day > end:
            raise PageviewError(
                f"{label}: pageview row {day.isoformat()} is outside the requested range"
            )
    return {
        "lang": item["lang"],
        "title": item["title"],
        "start": item["start"],
        "end": item["end"],
        "days": classify_days(start, end, counts),
    }


def _fetch_with_retries(url: str, fetch: GetJson, sleep: Callable[[float], None]) -> Any:
    for attempt in range(PAGEVIEW_MAX_ATTEMPTS):
        try:
            return fetch(url, {})
        except HttpError as exc:
            if exc.status_code == 404:
                raise PageviewError(PAGEVIEW_404_MESSAGE) from exc
            if not _retryable(exc) or attempt + 1 == PAGEVIEW_MAX_ATTEMPTS:
                raise PageviewError(str(exc)) from exc
            sleep(RETRY_DELAY_SECONDS)


def _retryable(error: HttpError) -> bool:
    if error.timed_out or error.status_code is None:
        return False
    return error.status_code == 429 or 500 <= error.status_code <= 599


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()
