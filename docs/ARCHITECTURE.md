# Architecture

```text
User request
    |
    v
AI agent
    |
    v
resolve
    |
    v
AI agent selects titles and writes series.json
    |
    v
report
    |
    v
pageviews.json
    |
    v
analysis.json, chart.png, report.pdf
    |
    v
AI agent explains analysis.json
```

`resolve` and `report` are the only commands. The model does not calculate, and the PDF does not contain model-written prose.

This milestone's `report` writes `pageviews.json` only. `analysis.json`, `chart.png`, and `report.pdf` come later. `report` does not resolve titles and does not expand a topic × language × period matrix.

## Modules

- `http.py` — JSON GET with an identifying User-Agent and timeout. HTTP status and timeout are recorded on `HttpError`. Retries are not done here.
- `resolve.py` — validates the resolve request, loads the query title with redirects, searches MediaWiki in `langs[0]` only when that page is missing or a disambiguation page, reads langlinks, returns one result per topic.
- `pageviews.py` — fetches daily pageviews for each series, retries 429 and 5xx, classifies days, and writes `pageviews.json`.
- `analyze.py` — validates `analysis.json`. Later it will calculate metrics. It does not fetch pageviews.
- `report.py` — validates `series.json`. Later it will write the chart and the one-page PDF from `analysis.json`.
- `__main__.py` — exposes `resolve` and `report`.

A disambiguation page is never a selected article. If a requested language has no langlink, the resolved result records `missing langlink: <lang>` and does not search that language separately.

`report` accepts an explicit list of series. It does not expand a topic × language × period matrix. The model builds that list:

- several topics: one series per chosen title, same dates
- several languages: one series per langlink title, same dates
- two time ranges: the same title twice, with different dates

## Resolve request

```json
{
  "topics": ["Python", "Java"],
  "langs": ["en", "uk"],
  "start": "2024-01-01",
  "end": "2024-12-31"
}
```

`topics` is a non-empty list of distinct strings. `langs[0]` is the source edition that is searched. `start` must be on or after 2015-07-01, and `end` must be on or after `start`.

## Resolve response

```json
{
  "langs": ["en", "uk"],
  "start": "2024-01-01",
  "end": "2024-12-31",
  "results": []
}
```

One result per topic, in the same order as `topics`. Result shape depends on `status`.

Resolved:

```json
{
  "query": "Python",
  "lang": "en",
  "status": "resolved",
  "title": "Python (programming language)",
  "pageid": 23862,
  "description": "general-purpose programming language",
  "langlinks": [{ "lang": "uk", "title": "Python" }],
  "notes": []
}
```

Ambiguous:

```json
{
  "query": "Mercury",
  "lang": "en",
  "status": "ambiguous",
  "candidates": [
    {
      "title": "Mercury (planet)",
      "pageid": 19007,
      "description": "innermost planet",
      "langlinks": [{ "lang": "uk", "title": "Меркурій (планета)" }]
    },
    {
      "title": "Mercury (element)",
      "pageid": 19019,
      "description": "chemical element",
      "langlinks": [{ "lang": "uk", "title": "Меркурій" }]
    }
  ],
  "notes": []
}
```

Not found:

```json
{
  "query": "zzznothinghere999",
  "lang": "en",
  "status": "not_found",
  "candidates": [],
  "notes": []
}
```

The agent stops before `report` unless every result is `resolved`. Titles in `series.json` must be copied exactly from a resolved `title` or a `langlinks[].title`.

## How resolve chooses a page

1. Load the query as a title on `{langs[0]}.wikipedia.org` with `redirects=1`. Read `pageprops`, `description`, and `langlinks`.
2. If that page exists and is not a disambiguation page, return it as `resolved`. Search order is not consulted.
3. If the page is missing or is a disambiguation page, search namespace 0.
4. Load each hit with `redirects=1`. Skip disambiguation pages.
5. If exactly one non-disambiguation article remains, return `resolved`.
6. If several distinct articles remain, return `ambiguous`.
7. If none remain, return `not_found`.

No pageview ranking, no search-rank choice, and no confidence score. A disambiguation page is never the selected article. The canonical title is the MediaWiki `title` of the selected page. Requested language titles come only from that page's `langlinks`.

Exact-title matches are deterministic MediaWiki lookups. They can still be semantically ambiguous for the user. Example: English `Java` resolves to the island article. If the user likely meant the programming language, the agent should ask before writing `series.json`.

## Series input

```json
{
  "series": [
    {
      "lang": "en",
      "title": "Mercury (planet)",
      "start": "2024-01-01",
      "end": "2024-03-31"
    }
  ]
}
```

## Analysis output

`analysis.json` will contain `series`, `caveats`, and `artifacts`. Each series carries the metric fields and day rows defined in `.cursor/skills/wikipedia-interest/references/metrics.md`. Day `status` is `observed`, `missing`, or `unavailable`. Missing views are 0. Unavailable views are null.

`caveats` is exactly:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size.
- Similar movement between series is not causation.

`report` does not calculate these fields yet. It writes `pageviews.json`, whose series keep `lang`, `title`, `start`, `end`, and `days`. Each day has `date`, `views`, and `status`. Missing views are 0. Unavailable views are null. The series title is the title from `series.json`, not a title taken from the pageview response.
