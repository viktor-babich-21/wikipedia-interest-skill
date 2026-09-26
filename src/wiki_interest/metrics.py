"""Deterministic pageview metrics for one normalized series.

Included days are ``observed`` and ``missing`` (missing as 0).
``unavailable`` days are excluded from every calculation below.
There are no R², coverage, or spike thresholds.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from wiki_interest import ContractError

INCLUDED = frozenset({"observed", "missing"})

NOTE_PERCENT_START_ZERO = "percent_change is null because start_views is 0"
NOTE_PERCENT_TOO_FEW = (
    "percent_change is null because fewer than two included days exist"
)


def included_days(days: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return observed and missing rows in order. Unavailable rows are dropped."""
    return [day for day in days if day["status"] in INCLUDED]


def calculate_series_metrics(
    *,
    lang: str,
    title: str,
    start: str,
    end: str,
    days: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute the Milestone 4 analysis fields for one series.

    Internal arithmetic is not rounded. Presentation may round later.
    """
    included = included_days(days)
    values = [int(day["views"]) for day in included]
    notes: list[str] = []

    start_date = date.fromisoformat(start)
    end_date = date.fromisoformat(end)
    days_expected = (end_date - start_date).days + 1
    days_observed = sum(1 for day in days if day["status"] == "observed")
    days_missing = sum(1 for day in days if day["status"] == "missing")
    days_unavailable = sum(1 for day in days if day["status"] == "unavailable")
    if days_observed + days_missing + days_unavailable != days_expected:
        raise ContractError(
            "days_observed + days_missing + days_unavailable must equal days_expected"
        )

    # Observed counts only; missing contribute zero and unavailable are out.
    total_views = sum(int(day["views"]) for day in days if day["status"] == "observed")

    mean_daily_views: float | None
    median_daily_views: float | None
    start_views: int | None
    end_views: int | None
    if not values:
        mean_daily_views = None
        median_daily_views = None
        start_views = None
        end_views = None
    else:
        mean_daily_views = sum(values) / len(values)
        median_daily_views = _median(values)
        start_views = values[0]
        end_views = values[-1]

    percent_change = _percent_change(start_views, end_views, len(values), notes)
    slope, r_squared = _ols(values)
    busiest_day, busiest_day_views, busiest_day_share = _busiest(included, total_views)

    return {
        "lang": lang,
        "title": title,
        "start": start,
        "end": end,
        "total_views": total_views,
        "mean_daily_views": mean_daily_views,
        "median_daily_views": median_daily_views,
        "start_views": start_views,
        "end_views": end_views,
        "percent_change": percent_change,
        "slope_views_per_day": slope,
        "r_squared": r_squared,
        "busiest_day": busiest_day,
        "busiest_day_views": busiest_day_views,
        "busiest_day_share": busiest_day_share,
        "days_expected": days_expected,
        "days_observed": days_observed,
        "days_missing": days_missing,
        "days_unavailable": days_unavailable,
        "days": list(days),
        "notes": notes,
    }


def _median(values: list[int]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def _percent_change(
    start_views: int | None,
    end_views: int | None,
    included_count: int,
    notes: list[str],
) -> float | None:
    if included_count < 2:
        notes.append(NOTE_PERCENT_TOO_FEW)
        return None
    if start_views == 0:
        notes.append(NOTE_PERCENT_START_ZERO)
        return None
    return (end_views - start_views) / start_views * 100


def _ols(values: list[int]) -> tuple[float | None, float | None]:
    """Ordinary least-squares slope and R² for y against index 0..n-1.

    The index counts included days in series order. Unavailable days are
    omitted, so they are not gaps in x.

    Constant series (all y equal) have a defined slope of 0, but R² is null
    because the total sum of squares is 0 and 0/0 is undefined. JSON never
    receives NaN.
    """
    n = len(values)
    if n < 2:
        return None, None

    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    ss_xx = 0.0
    ss_xy = 0.0
    ss_tot = 0.0
    for index, y in enumerate(values):
        dx = index - mean_x
        dy = y - mean_y
        ss_xx += dx * dx
        ss_xy += dx * dy
        ss_tot += dy * dy

    # ss_xx is zero only for n < 2, already handled.
    slope = ss_xy / ss_xx
    if ss_tot == 0.0:
        return slope, None

    ss_res = 0.0
    intercept = mean_y - slope * mean_x
    for index, y in enumerate(values):
        residual = y - (intercept + slope * index)
        ss_res += residual * residual
    return slope, 1.0 - ss_res / ss_tot


def _busiest(
    included: list[dict[str, Any]], total_views: int
) -> tuple[str | None, int | None, float | None]:
    if not included:
        return None, None, None
    best = included[0]
    for day in included[1:]:
        views = int(day["views"])
        best_views = int(best["views"])
        if views > best_views or (views == best_views and day["date"] < best["date"]):
            best = day
    views = int(best["views"])
    share = None if total_views == 0 else views / total_views
    return best["date"], views, share
