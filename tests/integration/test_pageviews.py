"""Pageview retrieval with mocked HTTP. No live network."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import patch

from wiki_interest import ContractError
from wiki_interest.http import HttpError
from wiki_interest.pageviews import (
    PAGEVIEW_MAX_ATTEMPTS,
    PAGEVIEWS_FILENAME,
    PageviewError,
    fetch_pageviews,
    write_pageviews,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pageviews"
TODAY = date(2026, 9, 26)


def _load(name: str) -> object:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _series(lang: str, title: str, start: str, end: str) -> dict[str, str]:
    return {"lang": lang, "title": title, "start": start, "end": end}


class ScriptedFetch:
    """Return queued payloads or errors. Records the pageview URL and any retry pause."""

    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = list(outcomes)
        self.urls: list[str] = []
        self.sleeps: list[float] = []

    def __call__(self, url: str, params: dict[str, str]) -> object:
        self.urls.append(url)
        self._assert_pageview_url(url)
        if params:
            raise AssertionError(params)
        if not self.outcomes:
            raise AssertionError(f"unexpected request {url}")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)

    @staticmethod
    def _assert_pageview_url(url: str) -> None:
        if "wikipedia.org/w/api.php" in url or "/pageviews/" not in url:
            raise AssertionError(url)


class PageviewIntegrationTests(unittest.TestCase):
    def test_successful_pageview_response(self) -> None:
        fetch = ScriptedFetch([_load("observed.json")])
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2024-01-01", "2024-01-02")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        series = result["series"][0]
        self.assertEqual(series["title"], "Python")
        self.assertEqual(
            series["days"],
            [
                {"date": "2024-01-01", "views": 120, "status": "observed"},
                {"date": "2024-01-02", "views": 90, "status": "observed"},
            ],
        )
        self.assertIn("/en.wikipedia/all-access/user/Python/daily/20240101/20240102", fetch.urls[0])
        self.assertEqual(fetch.sleeps, [])

    def test_multiple_series_in_one_report(self) -> None:
        fetch = ScriptedFetch([_load("observed.json"), _load("one_day.json")])
        result = fetch_pageviews(
            {
                "series": [
                    _series("en", "Python", "2024-01-01", "2024-01-02"),
                    _series("en", "Java", "2024-01-01", "2024-01-01"),
                ]
            },
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual([item["title"] for item in result["series"]], ["Python", "Java"])
        self.assertEqual(len(fetch.urls), 2)
        self.assertIn("/Python/daily/", fetch.urls[0])
        self.assertIn("/Java/daily/20240101/20240101", fetch.urls[1])

    def test_language_comparison_fetches_only_the_given_series(self) -> None:
        fetch = ScriptedFetch([_load("one_day.json"), _load("one_day.json")])
        result = fetch_pageviews(
            {
                "series": [
                    _series("en", "Python", "2024-01-01", "2024-01-01"),
                    _series("uk", "Python", "2024-01-01", "2024-01-01"),
                ]
            },
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual([item["lang"] for item in result["series"]], ["en", "uk"])
        self.assertEqual(len(fetch.urls), 2)
        self.assertIn("/en.wikipedia/all-access/user/Python/", fetch.urls[0])
        self.assertIn("/uk.wikipedia/all-access/user/Python/", fetch.urls[1])

    def test_period_comparison_repeats_one_title(self) -> None:
        older = _load("one_day.json")
        assert isinstance(older, dict)
        older["items"][0]["timestamp"] = "2023010100"
        fetch = ScriptedFetch([older, _load("one_day.json")])
        result = fetch_pageviews(
            {
                "series": [
                    _series("en", "Python", "2023-01-01", "2023-01-01"),
                    _series("en", "Python", "2024-01-01", "2024-01-01"),
                ]
            },
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(
            [(item["start"], item["end"]) for item in result["series"]],
            [("2023-01-01", "2023-01-01"), ("2024-01-01", "2024-01-01")],
        )
        self.assertEqual(len(fetch.urls), 2)
        self.assertIn("/daily/20230101/20230101", fetch.urls[0])
        self.assertIn("/daily/20240101/20240101", fetch.urls[1])

    def test_interior_missing_days_are_zero(self) -> None:
        fetch = ScriptedFetch([_load("gap.json")])
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2024-01-01", "2024-01-03")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(
            result["series"][0]["days"],
            [
                {"date": "2024-01-01", "views": 120, "status": "observed"},
                {"date": "2024-01-02", "views": 0, "status": "missing"},
                {"date": "2024-01-03", "views": 90, "status": "observed"},
            ],
        )

    def test_trailing_unavailable_days_stay_null(self) -> None:
        fetch = ScriptedFetch([_load("trailing.json")])
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2026-09-23", "2026-09-26")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(
            result["series"][0]["days"],
            [
                {"date": "2026-09-23", "views": 8, "status": "observed"},
                {"date": "2026-09-24", "views": None, "status": "unavailable"},
                {"date": "2026-09-25", "views": None, "status": "unavailable"},
                {"date": "2026-09-26", "views": None, "status": "unavailable"},
            ],
        )

    def test_retry_429_then_success(self) -> None:
        fetch = ScriptedFetch(
            [HttpError("HTTP 429 for pageviews", status_code=429), _load("observed.json")]
        )
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2024-01-01", "2024-01-02")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(result["series"][0]["days"][0]["views"], 120)
        self.assertEqual(len(fetch.urls), 2)
        self.assertEqual(fetch.sleeps, [1.0])

    def test_repeated_429_failure_writes_nothing(self) -> None:
        self.assertEqual(PAGEVIEW_MAX_ATTEMPTS, 3)
        fetch = ScriptedFetch(
            [HttpError("HTTP 429 for pageviews", status_code=429) for _ in range(3)]
        )
        series = {"series": [_series("en", "Python", "2024-01-01", "2024-01-02")]}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(PageviewError) as caught:
                write_pageviews(series, directory, fetch=fetch, sleep=fetch.sleep)
            self.assertIn("429", str(caught.exception))
            self.assertFalse((Path(directory) / PAGEVIEWS_FILENAME).exists())
        self.assertEqual(len(fetch.urls), 3)
        self.assertEqual(fetch.sleeps, [1.0, 1.0])

    def test_retry_500_then_success(self) -> None:
        fetch = ScriptedFetch(
            [HttpError("HTTP 500 for pageviews", status_code=500), _load("one_day.json")]
        )
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(result["series"][0]["days"][0]["status"], "observed")
        self.assertEqual(len(fetch.urls), 2)
        self.assertEqual(fetch.sleeps, [1.0])

    def test_repeated_5xx_failure(self) -> None:
        fetch = ScriptedFetch(
            [HttpError("HTTP 503 for pageviews", status_code=503) for _ in range(3)]
        )
        with self.assertRaises(PageviewError) as caught:
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
                fetch=fetch,
                                sleep=fetch.sleep,
            )
        self.assertIn("503", str(caught.exception))
        self.assertEqual(len(fetch.urls), 3)
        self.assertEqual(fetch.sleeps, [1.0, 1.0])

    def test_timeout_fails_without_retry(self) -> None:
        fetch = ScriptedFetch([HttpError("request timed out for pageviews", timed_out=True)])
        with self.assertRaises(PageviewError):
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
                fetch=fetch,
                                sleep=fetch.sleep,
            )
        self.assertEqual(len(fetch.urls), 1)
        self.assertEqual(fetch.sleeps, [])

    def test_malformed_json_fails(self) -> None:
        def fetch(url: str, params: dict[str, str]) -> object:
            recorded.append(url)
            text = (FIXTURES / "not_json.txt").read_text(encoding="utf-8")
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                raise HttpError(f"response from {url} is not JSON") from exc

        recorded: list[str] = []
        with self.assertRaises(PageviewError) as caught:
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
                fetch=fetch,
                                sleep=lambda _delay: recorded.append("slept"),
            )
        self.assertIn("not JSON", str(caught.exception))
        self.assertEqual(recorded, [recorded[0]])

    def test_invalid_api_response_shape(self) -> None:
        fetch = ScriptedFetch([_load("bad_shape.json")])
        with self.assertRaises(PageviewError):
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
                fetch=fetch,
                                sleep=fetch.sleep,
            )
        self.assertEqual(len(fetch.urls), 1)
        outside = ScriptedFetch([_load("observed.json")])
        with self.assertRaises(PageviewError) as caught:
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-01")]},
                fetch=outside,
                                sleep=outside.sleep,
            )
        self.assertIn("outside the requested range", str(caught.exception))

    def test_date_before_pageview_epoch_is_rejected(self) -> None:
        fetch = ScriptedFetch([])
        with self.assertRaises(ContractError):
            fetch_pageviews(
                {"series": [_series("en", "Python", "2015-06-30", "2015-07-02")]},
                fetch=fetch,
                                sleep=fetch.sleep,
            )
        self.assertEqual(fetch.urls, [])

    def test_unicode_title_is_encoded_and_not_replaced(self) -> None:
        fetch = ScriptedFetch([_load("one_day.json")])
        result = fetch_pageviews(
            {"series": [_series("uk", "Київ", "2024-01-01", "2024-01-01")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(result["series"][0]["title"], "Київ")
        self.assertNotIn("Київ", fetch.urls[0])
        self.assertIn("%D0%9A%D0%B8%D1%97%D0%B2", fetch.urls[0])
        self.assertIn("/uk.wikipedia/all-access/user/", fetch.urls[0])

    def test_parenthetical_title_is_encoded_and_not_replaced(self) -> None:
        fetch = ScriptedFetch([_load("one_day.json")])
        title = "Python (programming language)"
        result = fetch_pageviews(
            {"series": [_series("en", title, "2024-01-01", "2024-01-01")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        self.assertEqual(result["series"][0]["title"], title)
        self.assertIn("Python_%28programming_language%29", fetch.urls[0])
        self.assertNotIn(" ", fetch.urls[0])

    def test_all_zero_series_from_empty_items(self) -> None:
        fetch = ScriptedFetch([_load("empty_items.json")])
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2024-01-01", "2024-01-03")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        days = result["series"][0]["days"]
        self.assertEqual([day["status"] for day in days], ["missing", "missing", "missing"])
        self.assertTrue(all(day["views"] == 0 for day in days))

    def test_http_404_does_not_become_zero_views(self) -> None:
        from wiki_interest.pageviews import PAGEVIEW_404_MESSAGE

        fetch = ScriptedFetch([HttpError("HTTP 404 for pageviews", status_code=404)])
        with self.assertRaises(PageviewError) as caught:
            fetch_pageviews(
                {"series": [_series("en", "Python", "2024-01-01", "2024-01-03")]},
                fetch=fetch,
                sleep=fetch.sleep,
            )
        message = str(caught.exception)
        self.assertIn(PAGEVIEW_404_MESSAGE, message)
        self.assertIn("ambiguous", message.lower())
        self.assertEqual(len(fetch.urls), 1)
        self.assertEqual(fetch.sleeps, [])

    def test_range_ending_near_the_current_date(self) -> None:
        fetch = ScriptedFetch([_load("recent.json")])
        result = fetch_pageviews(
            {"series": [_series("en", "Python", "2026-09-24", "2026-09-26")]},
            fetch=fetch,
                        sleep=fetch.sleep,
        )
        days = result["series"][0]["days"]
        self.assertEqual(days[-1]["date"], TODAY.isoformat())
        self.assertEqual(days[-1], {"date": "2026-09-26", "views": None, "status": "unavailable"})
        self.assertEqual(days[0], {"date": "2026-09-24", "views": 15, "status": "observed"})
        self.assertEqual(days[1]["status"], "unavailable")

    def test_report_command_writes_pageviews_and_analysis_or_exits_nonzero(self) -> None:
        from wiki_interest.__main__ import main

        payload = _load("observed.json")

        def fetch(url: str, params: dict[str, str]) -> object:
            return payload

        with tempfile.TemporaryDirectory() as directory:
            series_path = Path(directory) / "series.json"
            out_dir = Path(directory) / "out"
            series_path.write_text(
                json.dumps({"series": [_series("en", "Python", "2024-01-01", "2024-01-02")]}),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with patch("wiki_interest.pageviews.get_json", fetch):
                with redirect_stdout(stdout):
                    code = main(["report", "--series", str(series_path), "--out-dir", str(out_dir)])
            self.assertEqual(code, 0)
            self.assertEqual(Path(stdout.getvalue().strip()), out_dir / "analysis.json")
            written = json.loads((out_dir / PAGEVIEWS_FILENAME).read_text(encoding="utf-8"))
            self.assertEqual(written["series"][0]["days"][0]["views"], 120)
            analysis = json.loads((out_dir / "analysis.json").read_text(encoding="utf-8"))
            series = analysis["series"][0]
            self.assertEqual(series["total_views"], 210)
            self.assertEqual(series["mean_daily_views"], 105.0)
            self.assertEqual(series["percent_change"], -25.0)
            self.assertEqual(series["slope_views_per_day"], -30.0)
            self.assertEqual(series["days_expected"], 2)
            self.assertEqual(
                series["days_observed"] + series["days_missing"] + series["days_unavailable"],
                series["days_expected"],
            )
            self.assertNotIn("NaN", (out_dir / "analysis.json").read_text(encoding="utf-8"))
            self.assertGreater((out_dir / "chart.png").stat().st_size, 0)
            self.assertGreater((out_dir / "report.pdf").stat().st_size, 0)

            series_path.write_text(
                json.dumps({"series": [_series("en", "Python", "2015-06-30", "2015-07-02")]}),
                encoding="utf-8",
            )
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                failed = main(["report", "--series", str(series_path), "--out-dir", str(out_dir)])
            self.assertEqual(failed, 1)
