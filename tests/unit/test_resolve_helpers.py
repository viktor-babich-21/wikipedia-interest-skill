"""Unit tests for MediaWiki response helpers. No network."""

from __future__ import annotations

import unittest

from wiki_interest.http import HttpError
from wiki_interest.resolve import ResolveError, _filter_langlinks, _normalize_title, _title_matches


class ResolveHelperTests(unittest.TestCase):
    def test_title_match_ignores_case_and_underscores(self) -> None:
        self.assertTrue(_title_matches("mercury (planet)", "Mercury_(planet)"))
        self.assertFalse(_title_matches("Mercury", "Mercury (planet)"))
        self.assertEqual(_normalize_title("  Foo_Bar  "), "foo bar")

    def test_filter_langlinks_keeps_requested_order(self) -> None:
        raw = [
            {"lang": "de", "title": "Python (Programmiersprache)"},
            {"lang": "uk", "title": "Python"},
            {"lang": "fr", "title": "Python (langage)"},
        ]
        self.assertEqual(
            _filter_langlinks(raw, ["uk", "de"]),
            [
                {"lang": "uk", "title": "Python"},
                {"lang": "de", "title": "Python (Programmiersprache)"},
            ],
        )
        self.assertEqual(_filter_langlinks(None, ["uk"]), [])

    def test_http_error_is_distinct(self) -> None:
        self.assertTrue(issubclass(HttpError, RuntimeError))
        self.assertTrue(issubclass(ResolveError, RuntimeError))
