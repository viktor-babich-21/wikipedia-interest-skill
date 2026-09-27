"""Analysis.json shape and construction from normalized pageview series.

Metric formulas live in ``metrics.py``. This module does not draw the chart or the PDF.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from wiki_interest import ContractError
from wiki_interest.metrics import calculate_series_metrics
from wiki_interest.resolve import parse_iso_date, validate_date_range

ANALYSIS_FILENAME = "analysis.json"
DEFAULT_CHART_NAME = "chart.png"
DEFAULT_PDF_NAME = "report.pdf"

DAY_STATUSES = ("observed", "missing", "unavailable")
CAVEATS = (
    "Page views measure attention to a Wikipedia article, not willingness to pay.",
    "Wikipedia editions differ in size. These figures are article pageviews.",
    "Similar movement between series is not causation.",
)

_TOP_KEYS = {"series", "caveats", "artifacts"}
_SERIES_KEYS = {
    "lang",
    "title",
    "start",
    "end",
    "total_views",
    "mean_daily_views",
    "median_daily_views",
    "start_views",
    "end_views",
    "percent_change",
    "slope_views_per_day",
    "r_squared",
    "busiest_day",
    "busiest_day_views",
    "busiest_day_share",
    "days_expected",
    "days_observed",
    "days_missing",
    "days_unavailable",
    "days",
    "notes",
}
_DAY_KEYS = {"date", "views", "status"}
_ARTIFACT_KEYS = {"chart", "pdf"}
_NULLABLE_NUMBERS = (
    "mean_daily_views",
    "median_daily_views",
    "start_views",
    "end_views",
    "percent_change",
    "slope_views_per_day",
    "r_squared",
    "busiest_day_views",
    "busiest_day_share",
)
_COUNT_FIELDS = (
    "total_views",
    "days_expected",
    "days_observed",
    "days_missing",
    "days_unavailable",
)


def build_analysis(
    pageviews: object,
    *,
    chart: str = DEFAULT_CHART_NAME,
    pdf: str = DEFAULT_PDF_NAME,
) -> dict[str, Any]:
    """Turn normalized pageview series into an analysis.json payload."""
    payload = _object(pageviews, "pageviews")
    if set(payload) != {"series"}:
        raise ContractError("pageviews keys must be ['series']")
    series = payload["series"]
    if not isinstance(series, list) or not series:
        raise ContractError("pageviews.series must be a non-empty list")
    analyzed = []
    for index, item in enumerate(series):
        row = _object(item, f"series[{index}]")
        analyzed.append(
            calculate_series_metrics(
                lang=_text(row.get("lang"), f"series[{index}].lang"),
                title=_text(row.get("title"), f"series[{index}].title"),
                start=_text(row.get("start"), f"series[{index}].start"),
                end=_text(row.get("end"), f"series[{index}].end"),
                days=_require_days(row.get("days"), index),
            )
        )
    return validate_analysis(
        {
            "series": analyzed,
            "caveats": list(CAVEATS),
            "artifacts": {"chart": chart, "pdf": pdf},
        }
    )


def write_analysis(
    pageviews: object,
    out_dir: str,
    *,
    chart: str = DEFAULT_CHART_NAME,
    pdf: str = DEFAULT_PDF_NAME,
) -> Path:
    """Build metrics and write analysis.json. Does not create chart or PDF files."""
    return write_analysis_data(build_analysis(pageviews, chart=chart, pdf=pdf), out_dir)


def write_analysis_data(analysis: object, out_dir: str) -> Path:
    """Write an already-built analysis payload. Does not create chart or PDF files."""
    validated = validate_analysis(analysis)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ANALYSIS_FILENAME
    path.write_text(
        json.dumps(validated, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def validate_analysis(data: object) -> dict[str, Any]:
    """Check analysis.json structure. Does not fetch pageviews."""
    payload = _object(data, "analysis")
    if set(payload) != _TOP_KEYS:
        raise ContractError(f"analysis keys must be {sorted(_TOP_KEYS)}")
    series = payload["series"]
    if not isinstance(series, list) or not series:
        raise ContractError("analysis.series must be a non-empty list")
    parsed_series = [_series(item, index) for index, item in enumerate(series)]
    caveats = payload["caveats"]
    if not isinstance(caveats, list) or list(caveats) != list(CAVEATS):
        raise ContractError("caveats must be the three fixed sentences")
    artifacts = _object(payload["artifacts"], "artifacts")
    if set(artifacts) != _ARTIFACT_KEYS:
        raise ContractError(f"artifacts keys must be {sorted(_ARTIFACT_KEYS)}")
    chart = artifacts["chart"]
    pdf = artifacts["pdf"]
    if not isinstance(chart, str) or not chart.strip():
        raise ContractError("artifacts.chart must be a non-empty string")
    if not isinstance(pdf, str) or not pdf.strip():
        raise ContractError("artifacts.pdf must be a non-empty string")
    return {
        "series": parsed_series,
        "caveats": list(CAVEATS),
        "artifacts": {"chart": chart, "pdf": pdf},
    }


def _require_days(value: object, index: int) -> list[dict[str, Any]]:
    field = f"series[{index}].days"
    if not isinstance(value, list):
        raise ContractError(f"{field} must be a list")
    return [dict(day) for day in value]


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def _series(data: object, index: int) -> dict[str, Any]:
    field = f"series[{index}]"
    item = _object(data, field)
    if set(item) != _SERIES_KEYS:
        raise ContractError(f"{field} keys do not match the analysis contract")
    validate_date_range(item["start"], item["end"])
    start = parse_iso_date(item["start"], "start")
    end = parse_iso_date(item["end"], "end")
    lang = item["lang"]
    title = item["title"]
    if not isinstance(lang, str) or not lang.strip():
        raise ContractError(f"{field}.lang must be a non-empty string")
    if not isinstance(title, str) or not title.strip():
        raise ContractError(f"{field}.title must be a non-empty string")
    parsed: dict[str, Any] = {"lang": lang, "title": title, "start": item["start"], "end": item["end"]}
    for name in _COUNT_FIELDS:
        parsed[name] = _count(item[name], f"{field}.{name}")
    for name in _NULLABLE_NUMBERS:
        parsed[name] = _nullable_number(item[name], f"{field}.{name}")
    busiest_day = item["busiest_day"]
    if busiest_day is not None:
        parsed_day = parse_iso_date(busiest_day, f"{field}.busiest_day")
        if parsed_day < start or parsed_day > end:
            raise ContractError(f"{field}.busiest_day must fall within the series range")
        busiest_day = parsed_day.isoformat()
    parsed["busiest_day"] = busiest_day
    share = parsed["busiest_day_share"]
    if share is not None and not 0 <= share <= 1:
        raise ContractError(f"{field}.busiest_day_share must be between 0 and 1 or null")
    days = item["days"]
    if not isinstance(days, list):
        raise ContractError(f"{field}.days must be a list")
    parsed["days"] = [
        _day(day, index, day_index, start, end) for day_index, day in enumerate(days)
    ]
    notes = item["notes"]
    if not isinstance(notes, list) or not all(isinstance(note, str) and note.strip() for note in notes):
        raise ContractError(f"{field}.notes must be a list of non-empty strings")
    parsed["notes"] = list(notes)
    return parsed


def _day(
    data: object, series_index: int, day_index: int, start: date, end: date
) -> dict[str, Any]:
    field = f"series[{series_index}].days[{day_index}]"
    item = _object(data, field)
    if set(item) != _DAY_KEYS:
        raise ContractError(f"{field} keys must be date, views, and status")
    day = parse_iso_date(item["date"], f"{field}.date")
    if day < start or day > end:
        raise ContractError(f"{field}.date must fall within the series range")
    status = item["status"]
    if status not in DAY_STATUSES:
        raise ContractError(f"{field}.status must be observed, missing, or unavailable")
    views = item["views"]
    if status == "unavailable":
        if views is not None:
            raise ContractError(f"{field}.views must be null when status is unavailable")
    elif status == "missing":
        if views != 0:
            raise ContractError(f"{field}.views must be 0 when status is missing")
    else:
        views = _count(views, f"{field}.views")
    return {"date": day.isoformat(), "views": views, "status": status}


def _count(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContractError(f"{field} must be an integer >= 0")
    return value


def _nullable_number(value: object, field: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{field} must be a number or null")
    return value


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value
