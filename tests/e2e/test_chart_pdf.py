"""Chart and PDF rendering from fixture analysis. No network."""

from __future__ import annotations

import math
import re
import tempfile
import unittest
import zlib
from pathlib import Path

import matplotlib.pyplot as plt

from wiki_interest.analyze import CAVEATS, build_analysis
from wiki_interest.chart import render_chart, write_chart
from wiki_interest.pdf_report import REPORT_TITLE, write_pdf

_MODEL_SENTENCE = "Interest surged because readers were willing to pay for the topic."


def _day(day: str, views: int | None, status: str) -> dict:
    return {"date": day, "views": views, "status": status}


def _series(lang: str, title: str, start: str, end: str, days: list[dict]) -> dict:
    return {"lang": lang, "title": title, "start": start, "end": end, "days": days}


def _gap_days() -> list[dict]:
    return [
        _day("2024-01-01", 10, "observed"),
        _day("2024-01-02", 0, "missing"),
        _day("2024-01-03", None, "unavailable"),
        _day("2024-01-04", 40, "observed"),
        _day("2024-01-05", 50, "observed"),
        _day("2024-01-06", 60, "observed"),
        _day("2024-01-07", 70, "observed"),
        _day("2024-01-08", 80, "observed"),
        _day("2024-01-09", 90, "observed"),
    ]


def _simple_days() -> list[dict]:
    return [
        _day("2024-01-01", 10, "observed"),
        _day("2024-01-02", 0, "missing"),
        _day("2024-01-03", 30, "observed"),
    ]


def _analysis(*series: dict) -> dict:
    return build_analysis({"series": list(series)})


def _gap_analysis() -> dict:
    return _analysis(_series("en", "Python", "2024-01-01", "2024-01-09", _gap_days()))


def _simple_analysis() -> dict:
    return _analysis(
        _series("en", "Python (programming language)", "2024-01-01", "2024-01-03", _simple_days())
    )


def _included_views(days: list[dict]) -> list[float]:
    return [float(day["views"]) for day in days if day["status"] != "unavailable"]


def _visual_average(values: list[float]) -> list[float]:
    averages = []
    for index in range(len(values)):
        window = values[max(0, index - 6) : index + 1]
        averages.append(sum(window) / len(window))
    return averages


def _finite(values: list[float]) -> list[float]:
    return [value for value in values if not math.isnan(value)]


def _pdf_page_count(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page(?!s)", data))


def _pdf_text(data: bytes) -> str:
    shown: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        raw = match.group(1)
        try:
            raw = zlib.decompress(raw)
        except zlib.error:
            pass
        if b"Tj" not in raw:
            continue
        shown.extend(_shown_literals(raw))
    return "\n".join(shown)


def _shown_literals(stream: bytes) -> list[str]:
    texts: list[str] = []
    index = 0
    size = len(stream)
    while index < size:
        if stream[index] != 0x28:
            index += 1
            continue
        text, index = _read_literal(stream, index)
        cursor = index
        while cursor < size and stream[cursor] in b" \t\r\n":
            cursor += 1
        if stream[cursor : cursor + 2] == b"Tj":
            texts.append(text)
    return texts


def _read_literal(stream: bytes, index: int) -> tuple[str, int]:
    index += 1
    chars = bytearray()
    depth = 1
    while index < len(stream) and depth:
        byte = stream[index]
        if byte == 0x5C:
            index += 1
            if index >= len(stream):
                break
            escaped = stream[index]
            mapped = {
                ord("n"): 10,
                ord("r"): 13,
                ord("t"): 9,
                ord("b"): 8,
                ord("f"): 12,
                ord("("): 40,
                ord(")"): 41,
                ord("\\"): 92,
            }
            if escaped in mapped:
                chars.append(mapped[escaped])
            elif ord("0") <= escaped <= ord("7"):
                octal = bytearray([escaped])
                for _ in range(2):
                    if index + 1 < len(stream) and ord("0") <= stream[index + 1] <= ord("7"):
                        index += 1
                        octal.append(stream[index])
                    else:
                        break
                chars.append(int(octal, 8) & 0xFF)
            else:
                chars.append(escaped)
        elif byte == 0x28:
            depth += 1
            chars.append(byte)
        elif byte == 0x29:
            depth -= 1
            if depth:
                chars.append(byte)
        else:
            chars.append(byte)
        index += 1
    return chars.decode("latin-1"), index


class ChartTests(unittest.TestCase):
    def tearDown(self) -> None:
        plt.close("all")

    def test_chart_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_chart(_simple_analysis(), directory)
            self.assertEqual(path, Path(directory) / "chart.png")
            self.assertTrue(path.is_file())

    def test_chart_file_is_non_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_chart(_simple_analysis(), directory)
            data = path.read_bytes()
            self.assertGreater(len(data), 0)
            self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_chart_contains_expected_number_of_series(self) -> None:
        figure = render_chart(_gap_analysis())
        daily = [
            line
            for line in figure.axes[0].get_lines()
            if not str(line.get_label()).endswith("(7-day average)")
        ]
        average = [
            line
            for line in figure.axes[0].get_lines()
            if str(line.get_label()).endswith("(7-day average)")
        ]
        self.assertEqual(len(daily), 1)
        self.assertEqual(len(average), 1)
        self.assertEqual(daily[0].get_label(), "en: Python")
        self.assertEqual(daily[0].get_color(), average[0].get_color())

    def test_missing_days_are_plotted_as_zero(self) -> None:
        figure = render_chart(_gap_analysis())
        daily = _daily_line(figure)
        views = [float(value) for value in daily.get_ydata()]
        self.assertEqual(views[1], 0.0)

    def test_unavailable_days_are_not_plotted_as_zero(self) -> None:
        figure = render_chart(_gap_analysis())
        daily = _daily_line(figure)
        views = [float(value) for value in daily.get_ydata()]
        self.assertTrue(math.isnan(views[2]))
        self.assertNotEqual(views[2], 0.0)

    def test_moving_average_is_based_on_daily_data(self) -> None:
        days = _gap_days()
        included = _included_views(days)
        expected = _visual_average(included)
        figure = render_chart(_gap_analysis())
        average = _average_line(figure)
        plotted = _finite([float(value) for value in average.get_ydata()])
        self.assertEqual(len(plotted), len(expected))
        for actual, wanted in zip(plotted, expected, strict=True):
            self.assertAlmostEqual(actual, wanted)
        self.assertAlmostEqual(expected[2], (10 + 0 + 40) / 3)
        self.assertNotAlmostEqual(expected[2], (10 + 0 + 0 + 40) / 4)
        self.assertAlmostEqual(expected[-1], sum(included[-7:]) / 7)
        self.assertEqual(len(included[-7:]), 7)
        self.assertNotAlmostEqual(expected[-1], sum(included) / len(included))


class PdfTests(unittest.TestCase):
    def test_pdf_is_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            chart = write_chart(_simple_analysis(), directory)
            path = write_pdf(_simple_analysis(), directory, chart)
            self.assertEqual(path, Path(directory) / "report.pdf")
            self.assertTrue(path.is_file())

    def test_pdf_is_exactly_one_page(self) -> None:
        data = _render_simple_pdf()
        self.assertEqual(_pdf_page_count(data), 1)

    def test_pdf_is_non_empty(self) -> None:
        data = _render_simple_pdf()
        self.assertGreater(len(data), 0)
        self.assertTrue(data.startswith(b"%PDF"))

    def test_pdf_contains_report_title(self) -> None:
        text = _pdf_text(_render_simple_pdf())
        self.assertIn(REPORT_TITLE, text)
        self.assertIn("Wikipedia article attention", text)

    def test_pdf_contains_known_metric_values(self) -> None:
        analysis = _simple_analysis()
        series = analysis["series"][0]
        self.assertEqual(series["total_views"], 40)
        self.assertEqual(series["mean_daily_views"], 40 / 3)
        self.assertEqual(series["percent_change"], 200.0)
        self.assertEqual(series["busiest_day"], "2024-01-03")
        self.assertEqual(series["busiest_day_views"], 30)
        self.assertEqual(series["busiest_day_share"], 0.75)
        text = _pdf_text(_render_simple_pdf())
        self.assertIn("Python (programming language)", text)
        self.assertIn("Date range 2024-01-01 to 2024-01-03", text)
        self.assertIn("Total views 40", text)
        self.assertIn("mean 13.3333", text)
        self.assertIn("median 10", text)
        self.assertIn("Start views 10", text)
        self.assertIn("end views 30", text)
        self.assertIn("percent change 200%", text)
        self.assertEqual(series["slope_views_per_day"], 10.0)
        self.assertIn("Slope 10", text)
        self.assertIn("R\u00b2 0.4286", text)
        self.assertIn("Busiest day 2024-01-03", text)
        self.assertIn("busiest-day views 30", text)
        self.assertIn("busiest-day share 0.75", text)
        self.assertIn("Days expected 3", text)
        self.assertIn("observed 2", text)
        self.assertIn("missing 1", text)
        self.assertIn("unavailable 0", text)

    def test_pdf_contains_fixed_caveats(self) -> None:
        text = _pdf_text(_render_simple_pdf())
        for caveat in CAVEATS:
            self.assertIn(caveat, text)
        self.assertIn(
            "Page views measure attention to a Wikipedia article, not willingness to pay.",
            text,
        )
        self.assertIn(
            "Wikipedia editions differ in size. These figures are article pageviews.",
            text,
        )
        self.assertIn("Similar movement between series is not causation.", text)

    def test_pdf_does_not_contain_model_generated_text(self) -> None:
        analysis = _analysis(
            _series(
                "en",
                "Python",
                "2024-01-01",
                "2024-01-02",
                [
                    _day("2024-01-01", 0, "observed"),
                    _day("2024-01-02", 5, "observed"),
                ],
            )
        )
        note = "percent_change is null because start_views is 0"
        self.assertEqual(analysis["series"][0]["percent_change"], None)
        self.assertIn(note, analysis["series"][0]["notes"])
        with tempfile.TemporaryDirectory() as directory:
            chart = write_chart(analysis, directory)
            pdf = write_pdf(analysis, directory, chart)
            text = _pdf_text(pdf.read_bytes())
        self.assertIn(note, text)
        self.assertIn("percent change n/a", text)
        self.assertNotIn(_MODEL_SENTENCE, text)
        self.assertNotIn("clear upward trend", text)

    def test_multiple_series_fixture_renders(self) -> None:
        analysis = _analysis(
            _series(
                "en",
                "Python (programming language)",
                "2024-01-01",
                "2024-01-02",
                [_day("2024-01-01", 10, "observed"), _day("2024-01-02", 20, "observed")],
            ),
            _series(
                "uk",
                "Python",
                "2024-04-01",
                "2024-04-02",
                [_day("2024-04-01", 3, "observed"), _day("2024-04-02", 4, "observed")],
            ),
        )
        figure = render_chart(analysis)
        labels = [str(line.get_label()) for line in figure.axes[0].get_lines()]
        self.assertEqual(len(labels), 4)
        self.assertIn("en: Python (programming language)", labels)
        self.assertIn("uk: Python", labels)
        colors = {
            line.get_label(): line.get_color()
            for line in figure.axes[0].get_lines()
            if not str(line.get_label()).endswith("(7-day average)")
        }
        self.assertEqual(len(set(colors.values())), 2)
        plt.close(figure)
        with tempfile.TemporaryDirectory() as directory:
            chart = write_chart(analysis, directory)
            pdf = write_pdf(analysis, directory, chart)
            data = pdf.read_bytes()
            text = _pdf_text(data)
        self.assertEqual(_pdf_page_count(data), 1)
        self.assertGreater(len(data), 0)
        self.assertIn("Date range varies by series", text)
        self.assertIn("en: Python (programming language)", text)
        self.assertIn("uk: Python", text)
        self.assertIn("2024-01-01 to 2024-01-02", text)
        self.assertIn("2024-04-01 to 2024-04-02", text)

    def test_unicode_title_renders_on_one_page(self) -> None:
        analysis = _analysis(
            _series(
                "uk",
                "Меркурій (планета)",
                "2024-01-01",
                "2024-01-02",
                [_day("2024-01-01", 8, "observed"), _day("2024-01-02", 9, "observed")],
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            chart = write_chart(analysis, directory)
            pdf = write_pdf(analysis, directory, chart)
            data = pdf.read_bytes()
        self.assertGreater(len(data), 0)
        self.assertEqual(_pdf_page_count(data), 1)
        text = _pdf_text(data)
        self.assertIn(REPORT_TITLE, text)
        self.assertIn(CAVEATS[1], text)


def _daily_line(figure):
    matches = [
        line
        for line in figure.axes[0].get_lines()
        if not str(line.get_label()).endswith("(7-day average)")
    ]
    return matches[0]


def _average_line(figure):
    matches = [
        line
        for line in figure.axes[0].get_lines()
        if str(line.get_label()).endswith("(7-day average)")
    ]
    return matches[0]


def _render_simple_pdf() -> bytes:
    analysis = _simple_analysis()
    with tempfile.TemporaryDirectory() as directory:
        chart = write_chart(analysis, directory)
        path = write_pdf(analysis, directory, chart)
        return path.read_bytes()
