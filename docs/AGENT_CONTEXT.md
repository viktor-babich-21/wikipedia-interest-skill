# Agent context

## Product goal

Let a cheap tool-using model compare attention to Wikipedia articles across topics, language editions, and time ranges, then explain a chart and a one-page PDF whose numbers came from code.

## Boundary

The model identifies topics, languages, and dates, decides when to ask a clarifying question, chooses among `resolve` candidates, assembles `series.json` from those titles, and explains `analysis.json`.

Python owns MediaWiki search, canonical titles, langlinks, pageview fetching, day classification, every metric, the chart, the PDF, and JSON validation.

The model must not invent titles or pageviews, recompute metrics, build chart data, or put its own numbers into the PDF. If a command fails, stop.

## Current milestone

Milestone 2: MediaWiki `resolve` is implemented. It searches `langs[0]`, follows redirects, rejects disambiguation pages, returns langlinks, and prints one result per topic. `report` still validates series JSON and exits. Pageviews, metrics, the chart, and the PDF are not implemented.

Next, when asked: implement pageview fetch and day classification inside `report`. Do not start that work as part of milestone 2.
