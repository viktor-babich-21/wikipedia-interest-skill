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

`report` writes `pageviews.json`, then `analysis.json`, then `chart.png` and `report.pdf` from the written analysis file. The chart and PDF do not recalculate metrics. `report` does not resolve titles and does not expand a topic × language × period matrix.

## Modules

- `http.py` — JSON GET with an identifying User-Agent and timeout. HTTP status and timeout are recorded on `HttpError`. Retries are not done here.
- `resolve.py` — validates the resolve request, loads the query title with redirects, searches MediaWiki in `langs[0]` only when that page is missing or a disambiguation page, reads langlinks, returns one result per topic.
- `pageviews.py` — fetches daily pageviews for each series, retries 429 and 5xx, classifies days, and writes `pageviews.json`.
- `metrics.py` — calculates one series from its normalized days. No chart, no PDF, no thresholds.
- `analyze.py` — builds and validates `analysis.json`. It does not fetch pageviews and it does not draw files.
- `chart.py` — draws `chart.png` from the day rows in `analysis.json`. No metric formulas.
- `pdf_report.py` — draws one-page `report.pdf` from `analysis.json` and `chart.png`. No metric formulas and no model prose.
- `report.py` — validates `series.json`, then writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`.
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

`analysis.json` contains `series`, `caveats`, and `artifacts`. Each series carries the metric fields and day rows defined in `.cursor/skills/wikipedia-interest/references/metrics.md`. Day `status` is `observed`, `missing`, or `unavailable`. Missing views are 0. Unavailable views are null.

Included days are `observed` and `missing`. Unavailable days stay in `days` but are excluded from total, mean, median, start, end, percent change, slope, R², and the busiest day. `metrics.py` owns those formulas. Stored numbers are not rounded. `r_squared` and `busiest_day_share` are plain numbers or null. They do not become trend or spike flags.

`caveats` is exactly:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size. These figures are article pageviews.
- Similar movement between series is not causation.

`artifacts.chart` and `artifacts.pdf` are the file names `report` writes in the output directory. The defaults are `chart.png` and `report.pdf`.

`report` also writes `pageviews.json`, whose series keep `lang`, `title`, `start`, `end`, and `days`. Each day has `date`, `views`, and `status`. The series title is the title from `series.json`, not a title taken from the pageview response. The command prints the `analysis.json` path.

## Chart

The chart exists so a reader can see the daily series without treating the picture as a second calculator. It uses `series[].days` from `analysis.json`.

- An observed day is plotted at its stored `views`.
- A missing day is plotted at 0.
- An unavailable day is a gap. It is not drawn as zero, and the line does not connect across it.

The dashed line is a 7-day moving average of included days, in order. At each included day the point is the mean of that day's views and at most six preceding included days. A missing day contributes its 0. An unavailable day is skipped, so it does not become a zero inside the window. The first included days use the shorter window that exists. This average is not written into `analysis.json` and it is not a headline metric.

Series share one pair of axes and use separate colors. The legend is `{lang}: {title}`. The average uses the same color and a dashed line.

The y-axis uses plain numbers. There is no scientific notation.

## PDF

The PDF is one page rendered from `analysis.json` and `chart.png`. It copies titles, languages, dates, metric fields, completeness counts, notes, and `caveats`. It does not recompute them. It does not contain a model-written paragraph, because that prose would not be tied to the tested numbers.

Display formatting does not change the stored JSON:

- null is shown as `n/a`
- integers, and floats that are whole numbers, have no decimal point
- other finite floats keep at most four digits after the decimal point, with trailing zeros removed, using Python's round-half-even formatting
- if four digits would show zero for a non-zero value, eight digits are used instead
- `percent_change` keeps the stored percent and gains a `%` label
- `busiest_day_share` stays the stored ratio and is not rescaled

When every series has the same `start` and `end`, the header shows that range. When they differ, the header says `Date range varies by series` and each series still shows its own dates. A title outside Latin-1 is drawn with DejaVu Sans, which ships with matplotlib. English labels stay in Helvetica.

## Model procedure

The agent workflow, `series.json` rules, ambiguity stops, and explanation limits are in `.cursor/skills/wikipedia-interest/SKILL.md`. Field definitions are in `.cursor/skills/wikipedia-interest/references/metrics.md`. The manual cheap-model review and its pass/fail record are in `eval/cases.md`. There is no automated model runner.
