"""Unit tests for deterministic pageview metrics. No network."""

from __future__ import annotations

import json
import unittest

from wiki_interest import ContractError
from wiki_interest.analyze import build_analysis
from wiki_interest.metrics import (
    NOTE_PERCENT_START_ZERO,
    NOTE_PERCENT_TOO_FEW,
    calculate_series_metrics,
)


def _day(date: str, views: int | None, status: str) -> dict:
    return {"date": date, "views": views, "status": status}


def _metrics(start: str, end: str, days: list[dict]) -> dict:
    return calculate_series_metrics(
        lang="en",
        title="Python",
        start=start,
        end=end,
        days=days,
    )


class MetricsTests(unittest.TestCase):
    def test_normal_series_totals_mean_median_start_end_and_change(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 10, "observed"),
                _day("2024-01-02", 20, "observed"),
                _day("2024-01-03", 30, "observed"),
            ],
        )
        self.assertEqual(result["total_views"], 60)
        self.assertEqual(result["mean_daily_views"], 20.0)
        self.assertEqual(result["median_daily_views"], 20.0)
        self.assertEqual(result["start_views"], 10)
        self.assertEqual(result["end_views"], 30)
        self.assertEqual(result["percent_change"], 200.0)
        self.assertEqual(result["notes"], [])
        self.assertEqual(result["days_expected"], 3)
        self.assertEqual(result["days_observed"], 3)
        self.assertEqual(result["days_missing"], 0)
        self.assertEqual(result["days_unavailable"], 0)

    def test_missing_days_treated_as_zero_in_mean_and_total(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 10, "observed"),
                _day("2024-01-02", 0, "missing"),
                _day("2024-01-03", 20, "observed"),
            ],
        )
        self.assertEqual(result["total_views"], 30)
        self.assertEqual(result["mean_daily_views"], 10.0)
        self.assertEqual(result["median_daily_views"], 10.0)
        self.assertEqual(result["days_missing"], 1)

    def test_unavailable_days_excluded_from_calculations(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-04",
            [
                _day("2024-01-01", 10, "observed"),
                _day("2024-01-02", 30, "observed"),
                _day("2024-01-03", None, "unavailable"),
                _day("2024-01-04", None, "unavailable"),
            ],
        )
        self.assertEqual(result["total_views"], 40)
        self.assertEqual(result["mean_daily_views"], 20.0)
        self.assertEqual(result["start_views"], 10)
        self.assertEqual(result["end_views"], 30)
        self.assertEqual(result["days_unavailable"], 2)
        self.assertEqual(result["days_observed"] + result["days_missing"] + result["days_unavailable"], 4)

    def test_percent_change_null_when_start_is_zero(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-02",
            [
                _day("2024-01-01", 0, "missing"),
                _day("2024-01-02", 5, "observed"),
            ],
        )
        self.assertIsNone(result["percent_change"])
        self.assertIn(NOTE_PERCENT_START_ZERO, result["notes"])

    def test_percent_change_null_when_fewer_than_two_included_days(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-02",
            [
                _day("2024-01-01", 9, "observed"),
                _day("2024-01-02", None, "unavailable"),
            ],
        )
        self.assertIsNone(result["percent_change"])
        self.assertIsNone(result["slope_views_per_day"])
        self.assertIsNone(result["r_squared"])
        self.assertIn(NOTE_PERCENT_TOO_FEW, result["notes"])

    def test_perfect_linear_series_slope_and_r_squared(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-04",
            [
                _day("2024-01-01", 0, "observed"),
                _day("2024-01-02", 10, "observed"),
                _day("2024-01-03", 20, "observed"),
                _day("2024-01-04", 30, "observed"),
            ],
        )
        self.assertAlmostEqual(result["slope_views_per_day"], 10.0)
        self.assertAlmostEqual(result["r_squared"], 1.0)

    def test_noisy_series_has_low_r_squared(self) -> None:
        # Alternating values have little linear trend relative to variance.
        result = _metrics(
            "2024-01-01",
            "2024-01-06",
            [
                _day("2024-01-01", 10, "observed"),
                _day("2024-01-02", 0, "observed"),
                _day("2024-01-03", 10, "observed"),
                _day("2024-01-04", 0, "observed"),
                _day("2024-01-05", 10, "observed"),
                _day("2024-01-06", 0, "observed"),
            ],
        )
        self.assertAlmostEqual(result["slope_views_per_day"], -0.8571428571428571)
        self.assertLess(result["r_squared"], 0.2)
        self.assertGreaterEqual(result["r_squared"], 0.0)

    def test_constant_series_slope_zero_and_r_squared_null(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 7, "observed"),
                _day("2024-01-02", 7, "observed"),
                _day("2024-01-03", 7, "observed"),
            ],
        )
        self.assertEqual(result["slope_views_per_day"], 0.0)
        self.assertIsNone(result["r_squared"])
        encoded = json.dumps(result, allow_nan=False)
        self.assertIn('"r_squared": null', encoded)
        self.assertNotIn("NaN", encoded)

    def test_busiest_day_and_share(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 5, "observed"),
                _day("2024-01-02", 40, "observed"),
                _day("2024-01-03", 5, "observed"),
            ],
        )
        self.assertEqual(result["busiest_day"], "2024-01-02")
        self.assertEqual(result["busiest_day_views"], 40)
        self.assertAlmostEqual(result["busiest_day_share"], 40 / 50)

    def test_busiest_day_tie_uses_earliest_date(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 9, "observed"),
                _day("2024-01-02", 9, "observed"),
                _day("2024-01-03", 1, "observed"),
            ],
        )
        self.assertEqual(result["busiest_day"], "2024-01-01")
        self.assertEqual(result["busiest_day_views"], 9)

    def test_all_zero_series(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 0, "missing"),
                _day("2024-01-02", 0, "missing"),
                _day("2024-01-03", 0, "observed"),
            ],
        )
        self.assertEqual(result["total_views"], 0)
        self.assertEqual(result["mean_daily_views"], 0.0)
        self.assertEqual(result["median_daily_views"], 0.0)
        self.assertEqual(result["start_views"], 0)
        self.assertEqual(result["end_views"], 0)
        self.assertIsNone(result["percent_change"])
        self.assertIn(NOTE_PERCENT_START_ZERO, result["notes"])
        self.assertEqual(result["slope_views_per_day"], 0.0)
        self.assertIsNone(result["r_squared"])
        self.assertEqual(result["busiest_day"], "2024-01-01")
        self.assertEqual(result["busiest_day_views"], 0)
        self.assertIsNone(result["busiest_day_share"])

    def test_one_included_day(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-02",
            [
                _day("2024-01-01", 12, "observed"),
                _day("2024-01-02", None, "unavailable"),
            ],
        )
        self.assertEqual(result["total_views"], 12)
        self.assertEqual(result["mean_daily_views"], 12.0)
        self.assertEqual(result["median_daily_views"], 12.0)
        self.assertEqual(result["start_views"], 12)
        self.assertEqual(result["end_views"], 12)
        self.assertIsNone(result["percent_change"])
        self.assertIsNone(result["slope_views_per_day"])
        self.assertIsNone(result["r_squared"])
        self.assertEqual(result["busiest_day"], "2024-01-01")

    def test_no_included_days(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-02",
            [
                _day("2024-01-01", None, "unavailable"),
                _day("2024-01-02", None, "unavailable"),
            ],
        )
        self.assertEqual(result["total_views"], 0)
        self.assertIsNone(result["mean_daily_views"])
        self.assertIsNone(result["median_daily_views"])
        self.assertIsNone(result["start_views"])
        self.assertIsNone(result["end_views"])
        self.assertIsNone(result["percent_change"])
        self.assertIsNone(result["slope_views_per_day"])
        self.assertIsNone(result["r_squared"])
        self.assertIsNone(result["busiest_day"])
        self.assertIsNone(result["busiest_day_views"])
        self.assertIsNone(result["busiest_day_share"])
        self.assertIn(NOTE_PERCENT_TOO_FEW, result["notes"])
        self.assertEqual(result["days_unavailable"], 2)

    def test_even_count_median_averages_middle_pair(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-04",
            [
                _day("2024-01-01", 1, "observed"),
                _day("2024-01-02", 3, "observed"),
                _day("2024-01-03", 7, "observed"),
                _day("2024-01-04", 9, "observed"),
            ],
        )
        self.assertEqual(result["median_daily_views"], 5.0)

    def test_completeness_counts_sum_to_expected(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-05",
            [
                _day("2024-01-01", 1, "observed"),
                _day("2024-01-02", 0, "missing"),
                _day("2024-01-03", 2, "observed"),
                _day("2024-01-04", None, "unavailable"),
                _day("2024-01-05", None, "unavailable"),
            ],
        )
        self.assertEqual(result["days_expected"], 5)
        self.assertEqual(
            result["days_observed"] + result["days_missing"] + result["days_unavailable"],
            result["days_expected"],
        )

    def test_linear_with_missing_zero_still_fits(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 0, "observed"),
                _day("2024-01-02", 0, "missing"),
                _day("2024-01-03", 0, "observed"),
            ],
        )
        self.assertEqual(result["slope_views_per_day"], 0.0)
        self.assertIsNone(result["r_squared"])

    def test_unavailable_gap_is_omitted_from_the_regression_index(self) -> None:
        # Included views are 0 then 10. Calendar spacing would make the slope 5.
        result = _metrics(
            "2024-01-01",
            "2024-01-03",
            [
                _day("2024-01-01", 0, "observed"),
                _day("2024-01-02", None, "unavailable"),
                _day("2024-01-03", 10, "observed"),
            ],
        )
        self.assertEqual(result["start_views"], 0)
        self.assertEqual(result["end_views"], 10)
        self.assertIsNone(result["percent_change"])
        self.assertIn(NOTE_PERCENT_START_ZERO, result["notes"])
        self.assertAlmostEqual(result["slope_views_per_day"], 10.0)
        self.assertAlmostEqual(result["r_squared"], 1.0)
        self.assertEqual(result["days_unavailable"], 1)

    def test_busiest_tie_uses_earliest_date_when_that_row_is_not_first(self) -> None:
        result = _metrics(
            "2024-01-01",
            "2024-01-02",
            [
                _day("2024-01-02", 9, "observed"),
                _day("2024-01-01", 9, "observed"),
            ],
        )
        self.assertEqual(result["busiest_day"], "2024-01-01")
        self.assertEqual(result["busiest_day_views"], 9)

    def test_inconsistent_completeness_counts_are_rejected(self) -> None:
        with self.assertRaises(ContractError):
            _metrics(
                "2024-01-01",
                "2024-01-05",
                [_day("2024-01-01", 1, "observed")],
            )

    def test_build_analysis_keeps_full_precision_and_null_r_squared(self) -> None:
        analysis = build_analysis(
            {
                "series": [
                    {
                        "lang": "en",
                        "title": "Python",
                        "start": "2024-01-01",
                        "end": "2024-01-03",
                        "days": [
                            _day("2024-01-01", 1, "observed"),
                            _day("2024-01-02", 1, "observed"),
                            _day("2024-01-03", None, "unavailable"),
                        ],
                    }
                ]
            }
        )
        series = analysis["series"][0]
        self.assertEqual(series["total_views"], 2)
        self.assertEqual(series["mean_daily_views"], 1.0)
        self.assertEqual(series["days_expected"], 3)
        self.assertEqual(series["days_unavailable"], 1)
        self.assertIsNone(series["r_squared"])
        self.assertEqual(series["slope_views_per_day"], 0.0)
        self.assertEqual(series["days"][2]["status"], "unavailable")
        encoded = json.dumps(analysis, allow_nan=False)
        self.assertNotIn("NaN", encoded)
        self.assertEqual(len(analysis["caveats"]), 3)


if __name__ == "__main__":
    unittest.main()
