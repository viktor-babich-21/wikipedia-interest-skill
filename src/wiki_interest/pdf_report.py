"""One-page report.pdf from analysis.json and chart.png.

Numbers are copied from the analysis payload and formatted for display.
Nothing in this module recalculates a metric. There is no model-written paragraph.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from fpdf import FPDF

from wiki_interest import ContractError
from wiki_interest.analyze import validate_analysis

REPORT_TITLE = "Wikipedia article attention"
_LINE_HEIGHT = 4.2
_MIN_CHART_MM = 32.0


def write_pdf(analysis: object, out_dir: str, chart_path: Path | str) -> Path:
    """Render report.pdf. Raises ContractError when the report exceeds one page."""
    payload = validate_analysis(analysis)
    chart = Path(chart_path)
    if not chart.is_file() or chart.stat().st_size <= 0:
        raise ContractError("chart.png must exist before the PDF is rendered")
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _artifact_name(payload, "pdf")
    pdf = FPDF(format="A4", unit="mm")
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    _draw(pdf, payload, chart)
    if pdf.pages_count != 1 or pdf.get_y() > pdf.h - pdf.b_margin + 0.2:
        raise ContractError("report PDF must be exactly one page")
    pdf.output(path)
    return path


def format_number(value: object) -> str:
    """Format one stored number for the PDF. Does not replace analysis.json.

    null is ``n/a``. Integers, and floats that are whole numbers, have no
    decimal point. Other finite floats use at most four digits after the
    decimal point, trailing zeros removed, with Python's round-half-even
    formatting. If four digits would hide a non-zero value, eight digits are
    used instead. Scientific notation is not used.
    """
    if value is None:
        return "n/a"
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError("PDF number must be a number or null")
    if isinstance(value, int):
        return str(value)
    if not math.isfinite(value):
        raise ContractError("PDF number must be finite")
    if value.is_integer():
        return str(int(value))
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    if text in {"0", "-0"}:
        text = f"{value:.8f}".rstrip("0").rstrip(".")
    return text


def format_percent(value: object) -> str:
    """Display a stored percent_change. The percent sign is a label, not a rescaling."""
    if value is None:
        return "n/a"
    return f"{format_number(value)}%"


def report_lines(analysis: dict[str, Any]) -> list[str]:
    """Fixed labels plus values copied from analysis.json."""
    series = analysis["series"]
    starts = {item["start"] for item in series}
    ends = {item["end"] for item in series}
    if len(starts) == 1 and len(ends) == 1:
        header = f"Date range {series[0]['start']} to {series[0]['end']}"
    else:
        header = "Date range varies by series"
    lines = [REPORT_TITLE, header]
    for item in series:
        lines.extend(_series_lines(item))
    lines.append("Caveats")
    lines.extend(analysis["caveats"])
    return lines


def _series_lines(item: dict[str, Any]) -> list[str]:
    lines = [
        f"{item['lang']}: {item['title']}",
        f"{item['start']} to {item['end']}",
        (
            f"Total views {format_number(item['total_views'])}; "
            f"mean {format_number(item['mean_daily_views'])}; "
            f"median {format_number(item['median_daily_views'])}"
        ),
        (
            f"Start views {format_number(item['start_views'])}; "
            f"end views {format_number(item['end_views'])}; "
            f"percent change {format_percent(item['percent_change'])}"
        ),
        (
            f"Slope {format_number(item['slope_views_per_day'])}; "
            f"R\u00b2 {format_number(item['r_squared'])}"
        ),
        (
            f"Busiest day {item['busiest_day'] if item['busiest_day'] is not None else 'n/a'}; "
            f"busiest-day views {format_number(item['busiest_day_views'])}; "
            f"busiest-day share {format_number(item['busiest_day_share'])}"
        ),
        (
            f"Days expected {item['days_expected']}; "
            f"observed {item['days_observed']}; "
            f"missing {item['days_missing']}; "
            f"unavailable {item['days_unavailable']}"
        ),
    ]
    for note in item["notes"]:
        lines.append(note)
    return lines


def _draw(pdf: FPDF, analysis: dict[str, Any], chart: Path) -> None:
    lines = report_lines(analysis)
    title, date_range, *rest = lines
    caveat_at = rest.index("Caveats")
    body = rest[:caveat_at]
    caveats = rest[caveat_at:]
    _write(pdf, title, 14, bold=True, height=7)
    _write(pdf, date_range, 10, height=5)
    for line in body:
        _write(pdf, line, 9)
    saved_x, saved_y = pdf.get_x(), pdf.get_y()
    caveat_height = sum(_height(pdf, line, 9 if line != "Caveats" else 10) for line in caveats)
    pdf.set_xy(saved_x, saved_y)
    bottom = pdf.h - pdf.b_margin
    available = bottom - pdf.get_y() - caveat_height - 2
    if available < _MIN_CHART_MM:
        raise ContractError("report PDF must be exactly one page")
    pixel_w, pixel_h = _png_size(chart)
    natural = pdf.epw * pixel_h / pixel_w
    draw_h = min(natural, available)
    draw_w = pdf.epw * draw_h / natural
    x = pdf.l_margin + (pdf.epw - draw_w) / 2
    pdf.image(chart, x=x, y=pdf.get_y(), w=draw_w, h=draw_h)
    pdf.set_y(pdf.get_y() + draw_h + 2)
    for line in caveats:
        _write(pdf, line, 10 if line == "Caveats" else 9, bold=(line == "Caveats"))


def _write(pdf: FPDF, text: str, size: float, *, bold: bool = False, height: float | None = None) -> None:
    _set_font(pdf, text, size, bold=bold)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        pdf.epw,
        height if height is not None else _LINE_HEIGHT,
        text,
        align="L",
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _height(pdf: FPDF, text: str, size: float) -> float:
    _set_font(pdf, text, size, bold=(text == "Caveats"))
    wrapped = pdf.multi_cell(
        pdf.epw,
        _LINE_HEIGHT,
        text,
        align="L",
        dry_run=True,
        output="LINES",
    )
    return _LINE_HEIGHT * max(1, len(wrapped))


def _set_font(pdf: FPDF, text: str, size: float, *, bold: bool) -> None:
    style = "B" if bold else ""
    if any(ord(char) > 255 for char in text):
        _ensure_dejavu(pdf)
        pdf.set_font("DejaVu", style, size)
        return
    pdf.set_font("Helvetica", style, size)


def _ensure_dejavu(pdf: FPDF) -> None:
    # Registered per document. Matplotlib ships the face used for non-Latin titles.
    if "dejavu" in pdf.fonts:
        return
    from matplotlib.font_manager import FontProperties, findfont

    regular = findfont(FontProperties(family="DejaVu Sans", weight="regular"))
    bold = findfont(FontProperties(family="DejaVu Sans", weight="bold"))
    pdf.add_font("DejaVu", "", regular)
    pdf.add_font("DejaVu", "B", bold)


def _png_size(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ContractError("chart file must be a PNG")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width <= 0 or height <= 0:
        raise ContractError("chart PNG has an empty image")
    return width, height


def _artifact_name(analysis: dict[str, Any], key: str) -> str:
    name = Path(str(analysis["artifacts"][key])).name
    if not name or name in {".", ".."}:
        raise ContractError(f"artifacts.{key} must be a file name")
    return name
