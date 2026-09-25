"""Minimal HTTP GET for JSON APIs."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

DEFAULT_USER_AGENT = (
    "wiki-interest/0.1 (Genesis AI Product Engineering School; educational)"
)
DEFAULT_TIMEOUT_SECONDS = 30

GetJson = Callable[[str, dict[str, str]], Any]


class HttpError(RuntimeError):
    """Raised when an HTTP request fails or returns non-JSON."""


def get_json(
    url: str,
    params: dict[str, str],
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    query = urllib.parse.urlencode(params)
    full_url = f"{url}?{query}" if query else url
    request = urllib.request.Request(
        full_url,
        headers={"User-Agent": user_agent, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            status = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HttpError(f"HTTP {exc.code} for {url}: {detail[:200]}") from exc
    except urllib.error.URLError as exc:
        raise HttpError(f"request failed for {url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise HttpError(f"request timed out for {url}") from exc

    if status is not None and status >= 400:
        raise HttpError(f"HTTP {status} for {url}")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise HttpError(f"response from {url} is not JSON") from exc
