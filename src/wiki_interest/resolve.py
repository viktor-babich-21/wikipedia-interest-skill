"""Resolve topics to Wikipedia articles via the MediaWiki Action API."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from wiki_interest import ContractError
from wiki_interest.http import GetJson, HttpError, get_json

EARLIEST_DATE = date(2015, 7, 1)
RESOLVE_STATUSES = ("resolved", "ambiguous", "not_found")
MISSING_LANGLINK_NOTE = "missing langlink: {lang}"
SEARCH_LIMIT = 8

_LANG = re.compile(r"^[a-z]{2,16}(?:-[a-z]{1,16}){0,2}$")
_REQUEST_KEYS = {"topics", "langs", "start", "end"}
_RESPONSE_KEYS = {"langs", "start", "end", "results"}
_RESOLVED_KEYS = {
    "query",
    "lang",
    "status",
    "title",
    "pageid",
    "description",
    "langlinks",
    "notes",
}
_AMBIGUOUS_KEYS = {"query", "lang", "status", "candidates", "notes"}
_NOT_FOUND_KEYS = {"query", "lang", "status", "candidates", "notes"}
_CANDIDATE_KEYS = {"title", "pageid", "description", "langlinks"}
_LANGLINK_KEYS = {"lang", "title"}


class ResolveError(RuntimeError):
    """Raised when MediaWiki resolution fails."""


def parse_iso_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        raise ContractError(f"{field} must be a YYYY-MM-DD string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{field} must be a YYYY-MM-DD string") from exc


def validate_date_range(start: object, end: object) -> None:
    start_date = parse_iso_date(start, "start")
    end_date = parse_iso_date(end, "end")
    if start_date < EARLIEST_DATE:
        raise ContractError("start must be on or after 2015-07-01")
    if end_date < start_date:
        raise ContractError("end must be on or after start")


def language_code(value: object, field: str) -> str:
    if not isinstance(value, str) or _LANG.fullmatch(value) is None:
        raise ContractError(f"{field} must be a Wikipedia language code")
    return value


def validate_resolve_request(data: object) -> dict[str, Any]:
    """Validate a multi-topic resolve request."""
    payload = _object(data, "resolve request")
    _exact_keys(payload, _REQUEST_KEYS, "resolve request")
    topics = _strings(payload["topics"], "topics")
    if len(topics) != len(set(topics)):
        raise ContractError("topics must not contain duplicates")
    langs = _langs(payload["langs"])
    validate_date_range(payload["start"], payload["end"])
    return {
        "topics": topics,
        "langs": langs,
        "start": payload["start"],
        "end": payload["end"],
    }


def validate_resolve_result(data: object, source_lang: str | None = None) -> dict[str, Any]:
    """Validate one per-topic resolve result. Shape depends on status."""
    result = _object(data, "resolve result")
    status = result.get("status")
    if status == "resolved":
        return _validate_resolved(result, source_lang)
    if status == "ambiguous":
        return _validate_ambiguous(result, source_lang)
    if status == "not_found":
        return _validate_not_found(result, source_lang)
    raise ContractError("status must be resolved, ambiguous, or not_found")


def validate_resolve_response(
    data: object, request: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Validate the resolve command output: one result per topic, in order."""
    payload = _object(data, "resolve response")
    _exact_keys(payload, _RESPONSE_KEYS, "resolve response")
    langs = _langs(payload["langs"])
    validate_date_range(payload["start"], payload["end"])
    results = payload["results"]
    if not isinstance(results, list) or not results:
        raise ContractError("results must be a non-empty list")
    source = langs[0]
    parsed = [validate_resolve_result(item, source) for item in results]
    for item in parsed:
        if item["status"] == "resolved":
            validate_resolved_against_request_langs(item, langs)
    queries = [item["query"] for item in parsed]
    if len(queries) != len(set(queries)):
        raise ContractError("result queries must not contain duplicates")
    if request is not None and queries != request["topics"]:
        raise ContractError("results must follow request topics in order")
    return {
        "langs": langs,
        "start": payload["start"],
        "end": payload["end"],
        "results": parsed,
    }


def needs_clarification(response: dict[str, Any]) -> bool:
    """True when the agent must stop before assembling series."""
    return any(item["status"] != "resolved" for item in response["results"])


def resolve_topics(
    request: dict[str, Any],
    *,
    fetch: GetJson | None = None,
) -> dict[str, Any]:
    """Resolve every topic in a validated request. Titles come only from MediaWiki."""
    validated = validate_resolve_request(request)
    client = fetch or get_json
    source = validated["langs"][0]
    results = [
        resolve_topic(topic, validated["langs"], fetch=client)
        for topic in validated["topics"]
    ]
    response = {
        "langs": validated["langs"],
        "start": validated["start"],
        "end": validated["end"],
        "results": results,
    }
    return validate_resolve_response(response, validated)


def resolve_topic(
    query: str,
    langs: list[str],
    *,
    fetch: GetJson | None = None,
) -> dict[str, Any]:
    """Resolve one topic in langs[0], then attach langlinks for the other langs."""
    if not langs:
        raise ContractError("langs must be a non-empty list")
    source = language_code(langs[0], "langs")
    target_langs = [language_code(item, "langs") for item in langs[1:]]
    client = fetch or get_json
    try:
        hits = _search(source, query, client)
        if not hits:
            return {
                "query": query,
                "lang": source,
                "status": "not_found",
                "candidates": [],
                "notes": [],
            }

        first_page: dict[str, Any] | None = None
        articles: list[dict[str, Any]] = []
        seen: set[int] = set()
        for index, hit in enumerate(hits):
            page = _load_page(source, hit, target_langs, client)
            if page is None:
                continue
            if index == 0:
                first_page = page
            if page["disambiguation"]:
                continue
            if page["pageid"] in seen:
                continue
            seen.add(page["pageid"])
            articles.append(page)

        if first_page is not None and not first_page["disambiguation"]:
            if _title_matches(query, hits[0]) or _title_matches(query, first_page["title"]):
                return _resolved_result(query, source, first_page, langs)

        if not articles:
            return {
                "query": query,
                "lang": source,
                "status": "not_found",
                "candidates": [],
                "notes": [],
            }
        if len(articles) == 1:
            return _resolved_result(query, source, articles[0], langs)
        return {
            "query": query,
            "lang": source,
            "status": "ambiguous",
            "candidates": [_candidate_payload(page) for page in articles[:5]],
            "notes": [],
        }
    except HttpError as exc:
        raise ResolveError(str(exc)) from exc


def _search(lang: str, query: str, fetch: GetJson) -> list[str]:
    payload = fetch(
        _api_url(lang),
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srnamespace": "0",
            "srlimit": str(SEARCH_LIMIT),
            "format": "json",
            "formatversion": "2",
        },
    )
    if not isinstance(payload, dict):
        raise ResolveError("search response must be an object")
    block = payload.get("query")
    if not isinstance(block, dict):
        raise ResolveError("search response is missing query")
    rows = block.get("search", [])
    if not isinstance(rows, list):
        raise ResolveError("search results must be a list")
    titles: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title)
    return titles


def _load_page(
    lang: str,
    title: str,
    target_langs: list[str],
    fetch: GetJson,
) -> dict[str, Any] | None:
    payload = fetch(
        _api_url(lang),
        {
            "action": "query",
            "titles": title,
            "redirects": "1",
            "prop": "info|pageprops|description|langlinks",
            "lllimit": "max",
            "format": "json",
            "formatversion": "2",
        },
    )
    if not isinstance(payload, dict):
        raise ResolveError("page response must be an object")
    block = payload.get("query")
    if not isinstance(block, dict):
        raise ResolveError("page response is missing query")
    pages = block.get("pages")
    if not isinstance(pages, list) or not pages:
        return None
    page = pages[0]
    if not isinstance(page, dict) or page.get("missing"):
        return None
    pageid = page.get("pageid")
    canonical = page.get("title")
    if not isinstance(pageid, int) or pageid <= 0:
        return None
    if not isinstance(canonical, str) or not canonical.strip():
        return None
    pageprops = page.get("pageprops") or {}
    disambiguation = isinstance(pageprops, dict) and "disambiguation" in pageprops
    description = page.get("description")
    if description is None:
        description = ""
    elif not isinstance(description, str):
        description = str(description)
    return {
        "title": canonical,
        "pageid": pageid,
        "description": description,
        "disambiguation": disambiguation,
        "langlinks": _filter_langlinks(page.get("langlinks"), target_langs),
    }


def _filter_langlinks(raw: object, target_langs: list[str]) -> list[dict[str, str]]:
    if not target_langs:
        return []
    wanted = set(target_langs)
    if not isinstance(raw, list):
        return []
    found: dict[str, str] = {}
    for item in raw:
        if not isinstance(item, dict):
            continue
        lang = item.get("lang")
        title = item.get("title")
        if lang in wanted and isinstance(title, str) and title.strip():
            found[lang] = title
    return [{"lang": lang, "title": found[lang]} for lang in target_langs if lang in found]


def _resolved_result(
    query: str, source: str, page: dict[str, Any], langs: list[str]
) -> dict[str, Any]:
    notes = []
    linked = {item["lang"] for item in page["langlinks"]}
    for lang in langs[1:]:
        if lang not in linked:
            notes.append(MISSING_LANGLINK_NOTE.format(lang=lang))
    return {
        "query": query,
        "lang": source,
        "status": "resolved",
        "title": page["title"],
        "pageid": page["pageid"],
        "description": page["description"],
        "langlinks": list(page["langlinks"]),
        "notes": notes,
    }


def _candidate_payload(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": page["title"],
        "pageid": page["pageid"],
        "description": page["description"],
        "langlinks": list(page["langlinks"]),
    }


def _title_matches(query: str, title: str) -> bool:
    return _normalize_title(query) == _normalize_title(title)


def _normalize_title(value: str) -> str:
    return " ".join(value.replace("_", " ").split()).casefold()


def _api_url(lang: str) -> str:
    return f"https://{lang}.wikipedia.org/w/api.php"


def _validate_resolved(result: dict[str, Any], source_lang: str | None) -> dict[str, Any]:
    _exact_keys(result, _RESOLVED_KEYS, "resolve result")
    query = _text(result["query"], "query")
    lang = language_code(result["lang"], "lang")
    if source_lang is not None and lang != source_lang:
        raise ContractError("result lang must be the first requested language")
    if result["status"] != "resolved":
        raise ContractError("status must be resolved")
    title = _text(result["title"], "title")
    pageid = result["pageid"]
    if isinstance(pageid, bool) or not isinstance(pageid, int) or pageid <= 0:
        raise ContractError("pageid must be a positive integer")
    description = result["description"]
    if not isinstance(description, str):
        raise ContractError("description must be a string")
    return {
        "query": query,
        "lang": lang,
        "status": "resolved",
        "title": title,
        "pageid": pageid,
        "description": description,
        "langlinks": _langlinks(result["langlinks"], lang),
        "notes": _notes(result["notes"]),
    }


def _validate_ambiguous(result: dict[str, Any], source_lang: str | None) -> dict[str, Any]:
    _exact_keys(result, _AMBIGUOUS_KEYS, "resolve result")
    query = _text(result["query"], "query")
    lang = language_code(result["lang"], "lang")
    if source_lang is not None and lang != source_lang:
        raise ContractError("result lang must be the first requested language")
    if result["status"] != "ambiguous":
        raise ContractError("status must be ambiguous")
    candidates = result["candidates"]
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise ContractError("ambiguous requires at least two candidates")
    parsed = [_candidate(item, index, lang) for index, item in enumerate(candidates)]
    return {
        "query": query,
        "lang": lang,
        "status": "ambiguous",
        "candidates": parsed,
        "notes": _notes(result["notes"]),
    }


def _validate_not_found(result: dict[str, Any], source_lang: str | None) -> dict[str, Any]:
    _exact_keys(result, _NOT_FOUND_KEYS, "resolve result")
    query = _text(result["query"], "query")
    lang = language_code(result["lang"], "lang")
    if source_lang is not None and lang != source_lang:
        raise ContractError("result lang must be the first requested language")
    if result["status"] != "not_found":
        raise ContractError("status must be not_found")
    candidates = result["candidates"]
    if not isinstance(candidates, list) or candidates:
        raise ContractError("not_found requires an empty candidates list")
    return {
        "query": query,
        "lang": lang,
        "status": "not_found",
        "candidates": [],
        "notes": _notes(result["notes"]),
    }


def _candidate(data: object, index: int, source_lang: str) -> dict[str, Any]:
    field = f"candidates[{index}]"
    candidate = _object(data, field)
    _exact_keys(candidate, _CANDIDATE_KEYS, field)
    pageid = candidate["pageid"]
    if isinstance(pageid, bool) or not isinstance(pageid, int) or pageid <= 0:
        raise ContractError(f"{field}.pageid must be a positive integer")
    description = candidate["description"]
    if not isinstance(description, str):
        raise ContractError(f"{field}.description must be a string")
    return {
        "title": _text(candidate["title"], f"{field}.title"),
        "pageid": pageid,
        "description": description,
        "langlinks": _langlinks(candidate["langlinks"], source_lang),
    }


def _langlinks(value: object, source_lang: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ContractError("langlinks must be a list")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        field = f"langlinks[{index}]"
        link = _object(item, field)
        _exact_keys(link, _LANGLINK_KEYS, field)
        lang = language_code(link["lang"], f"{field}.lang")
        if lang == source_lang:
            raise ContractError(f"{field}.lang duplicates the source language")
        if lang in seen:
            raise ContractError("langlinks has a duplicate lang")
        seen.add(lang)
        parsed.append({"lang": lang, "title": _text(link["title"], f"{field}.title")})
    return parsed


def _require_missing_langlink_notes_for_langs(
    langlinks: list[dict[str, str]], langs: list[str], notes: list[str]
) -> None:
    linked = {item["lang"] for item in langlinks}
    for lang in langs[1:]:
        if lang in linked:
            continue
        expected = MISSING_LANGLINK_NOTE.format(lang=lang)
        if expected not in notes:
            raise ContractError(f"missing language must be recorded as {expected!r}")


def validate_resolved_against_request_langs(
    result: dict[str, Any], langs: list[str]
) -> None:
    """Ensure a resolved result records every missing requested langlink."""
    if result["status"] != "resolved":
        return
    _require_missing_langlink_notes_for_langs(result["langlinks"], langs, result["notes"])


def _langs(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError("langs must be a non-empty list")
    langs = [language_code(item, "langs") for item in value]
    if len(langs) != len(set(langs)):
        raise ContractError("langs must not contain duplicates")
    return langs


def _strings(value: object, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{field} must be a non-empty list")
    return [_text(item, field) for item in value]


def _notes(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ContractError("notes must be a list")
    parsed = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ContractError("notes must contain non-empty strings")
        parsed.append(item)
    return parsed


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty string")
    return value


def _object(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{field} must be an object")
    return value


def _exact_keys(payload: dict[str, Any], expected: set[str], field: str) -> None:
    if set(payload) != expected:
        raise ContractError(f"{field} keys must be {sorted(expected)}")
