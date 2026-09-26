"""Pure pageview helpers. No network."""

from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from wiki_interest.http import HttpError
from wiki_interest.pageviews import (
    PAGEVIEW_404_MESSAGE,
    RETRY_DELAY_SECONDS,
    PageviewError,
    _retryable,
    classify_days,
    pageview_url,
    parse_pageview_items,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pageviews"


class PageviewHelperTests(unittest.TestCase):
    def test_gap_before_latest_stamp_is_missing_and_after_is_unavailable(self) -> None:
        days = classify_days(
            date(2026, 9, 23),
            date(2026, 9, 26),
            {date(2026, 9, 23): 8, date(2026, 9, 25): 4},
        )
        self.assertEqual(
            days,
            [
                {"date": "2026-09-23", "views": 8, "status": "observed"},
                {"date": "2026-09-24", "views": 0, "status": "missing"},
                {"date": "2026-09-25", "views": 4, "status": "observed"},
                {"date": "2026-09-26", "views": None, "status": "unavailable"},
            ],
        )

    def test_latest_stamp_is_published_through_boundary(self) -> None:
        days = classify_days(
            date(2026, 9, 23),
            date(2026, 9, 26),
            {date(2026, 9, 23): 8},
        )
        self.assertEqual(
            days,
            [
                {"date": "2026-09-23", "views": 8, "status": "observed"},
                {"date": "2026-09-24", "views": None, "status": "unavailable"},
                {"date": "2026-09-25", "views": None, "status": "unavailable"},
                {"date": "2026-09-26", "views": None, "status": "unavailable"},
            ],
        )

    def test_explicit_zero_stays_observed(self) -> None:
        days = classify_days(date(2024, 1, 1), date(2024, 1, 1), {date(2024, 1, 1): 0})
        self.assertEqual(days, [{"date": "2024-01-01", "views": 0, "status": "observed"}])

    def test_empty_items_range_is_all_missing(self) -> None:
        days = classify_days(date(2024, 1, 1), date(2024, 1, 2), {})
        self.assertEqual([day["status"] for day in days], ["missing", "missing"])
        self.assertTrue(all(day["views"] == 0 for day in days))

    def test_parse_fixture_and_reject_bad_shapes(self) -> None:
        parsed = parse_pageview_items(
            json.loads((FIXTURES / "observed.json").read_text(encoding="utf-8"))
        )
        self.assertEqual(parsed, {date(2024, 1, 1): 120, date(2024, 1, 2): 90})
        with self.assertRaises(PageviewError):
            parse_pageview_items(
                json.loads((FIXTURES / "bad_shape.json").read_text(encoding="utf-8"))
            )
        with self.assertRaises(PageviewError):
            parse_pageview_items({"items": [{"timestamp": "2024010100", "views": True}]})
        with self.assertRaises(PageviewError):
            parse_pageview_items(
                {
                    "items": [
                        {"timestamp": "2024010100", "views": 1},
                        {"timestamp": "2024010100", "views": 2},
                    ]
                }
            )
        with self.assertRaises(PageviewError):
            parse_pageview_items([])

    def test_url_keeps_language_access_agent_and_daily_granularity(self) -> None:
        url = pageview_url(
            "en", "Python (programming language)", date(2024, 1, 1), date(2024, 1, 2)
        )
        self.assertIn("/en.wikipedia/all-access/user/", url)
        self.assertIn("/daily/20240101/20240102", url)
        self.assertIn("Python_%28programming_language%29", url)
        self.assertNotIn(" ", url)

    def test_404_message_surfaces_ambiguity(self) -> None:
        lowered = PAGEVIEW_404_MESSAGE.lower()
        self.assertIn("ambiguous", lowered)
        self.assertIn("zero", lowered)
        self.assertIn("not yet loaded", lowered)
        self.assertIn("refusing", lowered)

    def test_retryable_statuses_are_only_429_and_5xx(self) -> None:
        self.assertEqual(RETRY_DELAY_SECONDS, 1.0)
        self.assertTrue(_retryable(HttpError("limited", status_code=429)))
        self.assertTrue(_retryable(HttpError("down", status_code=503)))
        self.assertFalse(_retryable(HttpError("missing", status_code=404)))
        self.assertFalse(_retryable(HttpError("slow", timed_out=True)))
        self.assertFalse(_retryable(HttpError("not json")))


if __name__ == "__main__":
    unittest.main()
