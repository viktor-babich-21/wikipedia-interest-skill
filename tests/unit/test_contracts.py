"""Contract checks that do not call the network."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import wiki_interest
from wiki_interest import ContractError
from wiki_interest.__main__ import main
from wiki_interest.analyze import CAVEATS, validate_analysis
from wiki_interest.report import validate_series_input
from wiki_interest.resolve import (
    needs_clarification,
    validate_resolve_request,
    validate_resolve_response,
    validate_resolve_result,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _analysis() -> dict:
    return {
        "series": [
            {
                "lang": "en",
                "title": "Python (programming language)",
                "start": "2024-01-01",
                "end": "2024-01-03",
                "total_views": 10,
                "mean_daily_views": 5,
                "median_daily_views": 5,
                "start_views": 4,
                "end_views": 6,
                "percent_change": 50,
                "slope_views_per_day": 1,
                "r_squared": 0.25,
                "busiest_day": "2024-01-02",
                "busiest_day_views": 6,
                "busiest_day_share": 0.6,
                "days_expected": 3,
                "days_observed": 2,
                "days_missing": 1,
                "days_unavailable": 0,
                "days": [
                    {"date": "2024-01-01", "views": 4, "status": "observed"},
                    {"date": "2024-01-02", "views": 6, "status": "observed"},
                    {"date": "2024-01-03", "views": 0, "status": "missing"},
                ],
                "notes": [],
            }
        ],
        "caveats": list(CAVEATS),
        "artifacts": {"chart": "chart.png", "pdf": "report.pdf"},
    }


class ContractTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(wiki_interest.__version__, "0.1.0")

    def test_resolve_request_accepts_two_topics(self) -> None:
        payload = json.loads((FIXTURES / "resolve_request.json").read_text(encoding="utf-8"))
        parsed = validate_resolve_request(payload)
        self.assertEqual(parsed["topics"], ["Python", "Java"])

    def test_resolve_request_rejects_early_and_inverted_dates(self) -> None:
        base = {"topics": ["Python"], "langs": ["en"], "start": "2015-06-30", "end": "2015-07-02"}
        with self.assertRaises(ContractError):
            validate_resolve_request(base)
        base["start"] = "2024-02-01"
        base["end"] = "2024-01-01"
        with self.assertRaises(ContractError):
            validate_resolve_request(base)

    def test_ambiguous_mercury_result(self) -> None:
        result = {
            "query": "Mercury",
            "lang": "en",
            "status": "ambiguous",
            "candidates": [
                {
                    "title": "Mercury (planet)",
                    "pageid": 19007,
                    "description": "innermost planet",
                    "langlinks": [{"lang": "uk", "title": "Меркурій (планета)"}],
                },
                {
                    "title": "Mercury (element)",
                    "pageid": 19019,
                    "description": "chemical element",
                    "langlinks": [{"lang": "uk", "title": "Меркурій (елемент)"}],
                },
            ],
            "notes": [],
        }
        parsed = validate_resolve_result(result)
        self.assertEqual(parsed["status"], "ambiguous")
        self.assertEqual(len(parsed["candidates"]), 2)

    def test_response_follows_topic_order_and_stops_when_ambiguous(self) -> None:
        request = validate_resolve_request(
            {"topics": ["Python", "Java"], "langs": ["en"], "start": "2024-01-01", "end": "2024-12-31"}
        )
        response = {
            "langs": ["en"],
            "start": "2024-01-01",
            "end": "2024-12-31",
            "results": [
                {
                    "query": "Python",
                    "lang": "en",
                    "status": "resolved",
                    "title": "Python (programming language)",
                    "pageid": 23862,
                    "description": "programming language",
                    "langlinks": [],
                    "notes": [],
                },
                {
                    "query": "Java",
                    "lang": "en",
                    "status": "ambiguous",
                    "candidates": [
                        {
                            "title": "Java (programming language)",
                            "pageid": 15881,
                            "description": "programming language",
                            "langlinks": [],
                        },
                        {
                            "title": "Java",
                            "pageid": 43148,
                            "description": "island of Indonesia",
                            "langlinks": [],
                        },
                    ],
                    "notes": [],
                },
            ],
        }
        parsed = validate_resolve_response(response, request)
        self.assertTrue(needs_clarification(parsed))

    def test_missing_langlink_must_be_recorded(self) -> None:
        result = {
            "query": "Python",
            "lang": "en",
            "status": "resolved",
            "title": "Python (programming language)",
            "pageid": 23862,
            "description": "programming language",
            "langlinks": [],
            "notes": [],
        }
        response = {
            "langs": ["en", "uk"],
            "start": "2024-01-01",
            "end": "2024-12-31",
            "results": [result],
        }
        with self.assertRaises(ContractError):
            validate_resolve_response(response)
        result["notes"] = ["missing langlink: uk"]
        parsed = validate_resolve_response(response)
        self.assertIn("missing langlink: uk", parsed["results"][0]["notes"])

    def test_series_allows_topics_and_separate_ranges(self) -> None:
        topics = validate_series_input(
            {
                "series": [
                    {
                        "lang": "en",
                        "title": "Python (programming language)",
                        "start": "2024-01-01",
                        "end": "2024-12-31",
                    },
                    {
                        "lang": "en",
                        "title": "Java (programming language)",
                        "start": "2024-01-01",
                        "end": "2024-12-31",
                    },
                ]
            }
        )
        self.assertEqual(len(topics["series"]), 2)
        ranges = validate_series_input(
            {
                "series": [
                    {
                        "lang": "en",
                        "title": "Python (programming language)",
                        "start": "2024-01-01",
                        "end": "2024-03-31",
                    },
                    {
                        "lang": "en",
                        "title": "Python (programming language)",
                        "start": "2024-04-01",
                        "end": "2024-06-30",
                    },
                ]
            }
        )
        self.assertEqual(ranges["series"][0]["title"], ranges["series"][1]["title"])

    def test_analysis_shape_and_day_status_rules(self) -> None:
        parsed = validate_analysis(_analysis())
        self.assertEqual(parsed["caveats"], list(CAVEATS))
        broken = _analysis()
        broken["series"][0]["days"][2]["views"] = None
        with self.assertRaises(ContractError):
            validate_analysis(broken)
        unavailable = _analysis()
        unavailable["series"][0]["days"][2] = {
            "date": "2024-01-03",
            "views": 0,
            "status": "unavailable",
        }
        with self.assertRaises(ContractError):
            validate_analysis(unavailable)

    def test_commands_validate_then_stop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text(
                json.dumps(
                    {
                        "topics": ["Python"],
                        "langs": ["en"],
                        "start": "2024-01-01",
                        "end": "2024-01-31",
                    }
                ),
                encoding="utf-8",
            )
            fake = {
                "langs": ["en"],
                "start": "2024-01-01",
                "end": "2024-01-31",
                "results": [
                    {
                        "query": "Python",
                        "lang": "en",
                        "status": "resolved",
                        "title": "Python (programming language)",
                        "pageid": 23862,
                        "description": "programming language",
                        "langlinks": [],
                        "notes": [],
                    }
                ],
            }
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                with patch("wiki_interest.__main__.resolve_topics", return_value=fake):
                    self.assertEqual(main(["resolve", "--request", str(request)]), 0)
                request.write_text(json.dumps({"topics": []}), encoding="utf-8")
                self.assertEqual(main(["resolve", "--request", str(request)]), 1)
                with self.assertRaises(SystemExit):
                    main(["fetch"])
