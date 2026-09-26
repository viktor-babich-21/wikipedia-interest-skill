"""Draw chart.png from analysis.json.

The daily line uses the stored day rows. Missing days are plotted as zero.
Unavailable days are gaps, not zeros. The dashed line is a 7-day visual
average of included days. It is not a metric and it is not written back
to analysis.json.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter

from wiki_interest import ContractError
from wiki_interest.analyze import validate_analysis

VISUAL_WINDOW = 7


def write_chart(analysis: object, out_dir: str) -> Path:
    """Render chart.png beside analysis.json. Does not calculate metrics."""
    payload = validate_analysis(analysis)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _artifact_name(payload, "chart")
    figure = render_chart(payload)
    try:
        figure.savefig(path, dpi=120, bbox_inches="tight", facecolor="white")
    finally:
        plt.close(figure)
    return path


def render_chart(analysis: object) -> Figure:
    """Build the chart figure from an analysis payload. Caller closes it."""
    payload = validate_analysis(analysis)
    figure, axes = plt.subplots(figsize=(7.4, 3.4), dpi=120)
    for index, series in enumerate(payload["series"]):
        _draw_series(axes, series, f"C{index % 10}")
    axes.set_title("Daily views and 7-day average")
    axes.set_xlabel("Date")
    axes.set_ylabel("Views")
    formatter = ScalarFormatter(useOffset=False)
    formatter.set_scientific(False)
    axes.yaxis.set_major_formatter(formatter)
    locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
    axes.xaxis.set_major_locator(locator)
    axes.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    axes.legend(fontsize=7, frameon=False)
    figure.autofmt_xdate(rotation=30, ha="right")
    figure.tight_layout()
    return figure


def series_plot_values(
    days: list[dict[str, Any]],
) -> tuple[list[datetime], list[float], list[float]]:
    """Return dates, daily views, and the visual 7-day average.

    Daily values copy ``views`` for observed and missing days. Unavailable
    days are NaN so the line breaks. The average at each included day is the
    mean of that day and at most six preceding included days. Missing views
    stay 0 inside that window. Unavailable days are left out of it.
    """
    dates = [datetime.combine(date.fromisoformat(day["date"]), datetime.min.time()) for day in days]
    daily: list[float] = []
    included: list[float] = []
    included_at: list[int] = []
    for index, day in enumerate(days):
        if day["status"] == "unavailable":
            daily.append(math.nan)
            continue
        value = float(day["views"])
        daily.append(value)
        included.append(value)
        included_at.append(index)
    average = [math.nan] * len(days)
    for position, index in enumerate(included_at):
        window = included[max(0, position - (VISUAL_WINDOW - 1)) : position + 1]
        average[index] = sum(window) / len(window)
    return dates, daily, average


def _draw_series(axes: Axes, series: dict[str, Any], color: str) -> None:
    dates, daily, average = series_plot_values(series["days"])
    label = f"{series['lang']}: {series['title']}"
    axes.plot(dates, daily, color=color, linewidth=1.25, linestyle="-", label=label)
    axes.plot(
        dates,
        average,
        color=color,
        linewidth=1.0,
        linestyle="--",
        label=f"{label} (7-day average)",
    )


def _artifact_name(analysis: dict[str, Any], key: str) -> str:
    name = Path(str(analysis["artifacts"][key])).name
    if not name or name in {".", ".."}:
        raise ContractError(f"artifacts.{key} must be a file name")
    return name
