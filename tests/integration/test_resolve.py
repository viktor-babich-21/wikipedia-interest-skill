"""MediaWiki resolve integration tests with mocked HTTP. No live network."""

from __future__ import annotations

import json
import unittest
from typing import Any
from unittest.mock import patch

from wiki_interest.http import HttpError
from wiki_interest.resolve import ResolveError, resolve_topics


def _search(titles: list[str]) -> dict[str, Any]:
    return {"query": {"search": [{"title": title} for title in titles]}}


def _page(
    title: str,
    pageid: int,
    *,
    description: str = "",
    disambiguation: bool = False,
    langlinks: list[dict[str, str]] | None = None,
    missing: bool = False,
) -> dict[str, Any]:
    if missing:
        return {"query": {"pages": [{"title": title, "missing": True}]}}
    page: dict[str, Any] = {
        "pageid": pageid,
        "title": title,
        "description": description,
    }
    if disambiguation:
        page["pageprops"] = {"disambiguation": ""}
    if langlinks:
        page["langlinks"] = langlinks
    return {"query": {"pages": [page]}}


class FakeMediaWiki:
    """Route Action API calls by list=search vs titles= without touching the network."""

    def __init__(self) -> None:
        self.searches: dict[tuple[str, str], list[str]] = {}
        self.pages: dict[tuple[str, str], dict[str, Any]] = {}
        self.failures: dict[str, Exception] = {}

    def set_search(self, lang: str, query: str, titles: list[str]) -> None:
        self.searches[(lang, query)] = titles

    def set_page(self, lang: str, title: str, payload: dict[str, Any]) -> None:
        self.pages[(lang, title)] = payload

    def fail(self, lang: str, exc: Exception) -> None:
        self.failures[lang] = exc

    def __call__(self, url: str, params: dict[str, str]) -> Any:
        lang = url.split("//", 1)[1].split(".", 1)[0]
        if lang in self.failures:
            raise self.failures[lang]
        if params.get("list") == "search":
            key = (lang, params["srsearch"])
            if key not in self.searches:
                raise AssertionError(f"unexpected search {key}")
            return _search(self.searches[key])
        if "titles" in params:
            key = (lang, params["titles"])
            if key not in self.pages:
                raise AssertionError(f"unexpected page lookup {key}")
            return self.pages[key]
        raise AssertionError(f"unexpected params {params}")


class ResolveIntegrationTests(unittest.TestCase):
    def test_clear_resolved_topic(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "Python", ["Python", "Python (mythology)"])
        api.set_page(
            "en",
            "Python",
            _page(
                "Python (programming language)",
                23862,
                description="general-purpose programming language",
                langlinks=[{"lang": "uk", "title": "Python"}],
            ),
        )
        api.set_page(
            "en",
            "Python (mythology)",
            _page("Python (mythology)", 123, description="earth-dragon of Greek myth"),
        )
        response = resolve_topics(
            {
                "topics": ["Python"],
                "langs": ["en", "uk"],
                "start": "2024-01-01",
                "end": "2024-12-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["title"], "Python (programming language)")
        self.assertEqual(result["pageid"], 23862)
        self.assertEqual(result["langlinks"], [{"lang": "uk", "title": "Python"}])

    def test_multiple_topics(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "Python", ["Python"])
        api.set_search("en", "Java", ["Java (programming language)"])
        api.set_page(
            "en",
            "Python",
            _page("Python (programming language)", 23862, description="programming language"),
        )
        api.set_page(
            "en",
            "Java (programming language)",
            _page("Java (programming language)", 15881, description="programming language"),
        )
        response = resolve_topics(
            {
                "topics": ["Python", "Java"],
                "langs": ["en"],
                "start": "2024-01-01",
                "end": "2024-12-31",
            },
            fetch=api,
        )
        self.assertEqual(
            [item["title"] for item in response["results"]],
            ["Python (programming language)", "Java (programming language)"],
        )

    def test_ambiguous_mercury(self) -> None:
        api = FakeMediaWiki()
        api.set_search(
            "en",
            "Mercury",
            ["Mercury", "Mercury (planet)", "Mercury (element)"],
        )
        api.set_page("en", "Mercury", _page("Mercury", 1, disambiguation=True))
        api.set_page(
            "en",
            "Mercury (planet)",
            _page(
                "Mercury (planet)",
                19007,
                description="innermost planet",
                langlinks=[{"lang": "uk", "title": "Меркурій (планета)"}],
            ),
        )
        api.set_page(
            "en",
            "Mercury (element)",
            _page(
                "Mercury (element)",
                19019,
                description="chemical element",
                langlinks=[{"lang": "uk", "title": "Меркурій"}],
            ),
        )
        response = resolve_topics(
            {
                "topics": ["Mercury"],
                "langs": ["en", "uk"],
                "start": "2024-03-01",
                "end": "2024-03-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(
            [item["title"] for item in result["candidates"]],
            ["Mercury (planet)", "Mercury (element)"],
        )

    def test_redirect_to_canonical_title(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "U.S.A.", ["U.S.A."])
        api.set_page("en", "U.S.A.", _page("United States", 3434750, description="country"))
        response = resolve_topics(
            {
                "topics": ["U.S.A."],
                "langs": ["en"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["title"], "United States")
        self.assertEqual(result["pageid"], 3434750)

    def test_disambiguation_skipped_for_single_article(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "RareTopic", ["RareTopic", "RareTopic (film)"])
        api.set_page("en", "RareTopic", _page("RareTopic", 10, disambiguation=True))
        api.set_page(
            "en",
            "RareTopic (film)",
            _page("RareTopic (film)", 11, description="2020 film"),
        )
        response = resolve_topics(
            {
                "topics": ["RareTopic"],
                "langs": ["en"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["title"], "RareTopic (film)")

    def test_no_search_results(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "zzznothinghere999", [])
        response = resolve_topics(
            {
                "topics": ["zzznothinghere999"],
                "langs": ["en"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        self.assertEqual(response["results"][0]["status"], "not_found")
        self.assertEqual(response["results"][0]["candidates"], [])

    def test_langlinks_for_multiple_languages(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "Kyiv", ["Kyiv"])
        api.set_page(
            "en",
            "Kyiv",
            _page(
                "Kyiv",
                16822,
                description="capital of Ukraine",
                langlinks=[
                    {"lang": "uk", "title": "Київ"},
                    {"lang": "de", "title": "Kiew"},
                    {"lang": "fr", "title": "Kiev"},
                ],
            ),
        )
        response = resolve_topics(
            {
                "topics": ["Kyiv"],
                "langs": ["en", "uk", "de"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(
            result["langlinks"],
            [{"lang": "uk", "title": "Київ"}, {"lang": "de", "title": "Kiew"}],
        )
        self.assertEqual(result["notes"], [])

    def test_missing_langlink(self) -> None:
        api = FakeMediaWiki()
        api.set_search("en", "LocalOnly", ["LocalOnly"])
        api.set_page(
            "en",
            "LocalOnly",
            _page("LocalOnly", 99, description="english-only article", langlinks=[]),
        )
        response = resolve_topics(
            {
                "topics": ["LocalOnly"],
                "langs": ["en", "uk"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        result = response["results"][0]
        self.assertEqual(result["status"], "resolved")
        self.assertEqual(result["langlinks"], [])
        self.assertEqual(result["notes"], ["missing langlink: uk"])

    def test_unicode_article_title(self) -> None:
        api = FakeMediaWiki()
        api.set_search("uk", "Київ", ["Київ"])
        api.set_page(
            "uk",
            "Київ",
            _page("Київ", 1234, description="столиця України", langlinks=[]),
        )
        response = resolve_topics(
            {
                "topics": ["Київ"],
                "langs": ["uk"],
                "start": "2024-01-01",
                "end": "2024-01-31",
            },
            fetch=api,
        )
        self.assertEqual(response["results"][0]["title"], "Київ")

    def test_http_failure_and_malformed_json(self) -> None:
        api = FakeMediaWiki()
        api.fail("en", HttpError("HTTP 500 for https://en.wikipedia.org/w/api.php"))
        with self.assertRaises(ResolveError):
            resolve_topics(
                {
                    "topics": ["Python"],
                    "langs": ["en"],
                    "start": "2024-01-01",
                    "end": "2024-01-31",
                },
                fetch=api,
            )

        def bad_json(url: str, params: dict[str, str]) -> Any:
            raise HttpError(f"response from {url} is not JSON")

        with self.assertRaises(ResolveError):
            resolve_topics(
                {
                    "topics": ["Python"],
                    "langs": ["en"],
                    "start": "2024-01-01",
                    "end": "2024-01-31",
                },
                fetch=bad_json,
            )

    def test_cli_resolve_uses_resolver(self) -> None:
        import io
        import tempfile
        from contextlib import redirect_stdout
        from pathlib import Path

        from wiki_interest.__main__ import main

        api = FakeMediaWiki()
        api.set_search("en", "Python", ["Python"])
        api.set_page(
            "en",
            "Python",
            _page("Python (programming language)", 23862, description="programming language"),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text(
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
            with patch("wiki_interest.resolve.get_json", api):
                with redirect_stdout(io.StringIO()):
                    code = main(["resolve", "--request", str(path)])
            self.assertEqual(code, 0)
