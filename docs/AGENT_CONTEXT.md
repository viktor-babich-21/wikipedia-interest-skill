# Agent context

## Product goal

Let a cheap tool-using model compare attention to Wikipedia articles across topics, language editions, and time ranges, then explain a chart and a one-page PDF whose numbers came from code.

## Boundary

The model identifies topics, languages, and dates, decides when to ask a clarifying question, chooses among `resolve` candidates, assembles `series.json` from those titles, and explains `analysis.json`.

Python owns MediaWiki search, canonical titles, langlinks, pageview fetching, day classification, every metric, the chart, the PDF, and JSON validation.

The model must not invent titles or pageviews, recompute metrics, build chart data, or put its own numbers into the PDF. If a command fails, stop.

## Current milestone

Milestone 3: `report` fetches daily pageviews for the explicit series list and writes `pageviews.json`. Days after the latest returned timestamp are unavailable; earlier omitted days are missing. HTTP 404 fails closed as ambiguous and never becomes zeros. Exact-title resolution is deterministic but can still need user clarification for queries such as `Java`. Metrics, the chart, and the PDF are not implemented.

`resolve` loads the query title with redirects. A non-disambiguation page is the result. Search rank does not choose an article. A disambiguation page is never selected.

Next, when asked: implement metric calculations. Do not start that work as part of milestone 3.
