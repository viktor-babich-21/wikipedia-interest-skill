# Agent context

## Product goal

Let a cheap tool-using model compare attention to Wikipedia articles across topics, language editions, and time ranges, then explain a chart and a one-page PDF whose numbers came from code.

## Boundary

The model identifies topics, languages, and dates, decides when to ask a clarifying question, chooses among `resolve` candidates, assembles `series.json` from those titles, and explains `analysis.json`.

Python owns MediaWiki search, canonical titles, langlinks, pageview fetching, day classification, every metric, the chart, the PDF, and JSON validation.

The model must not invent titles or pageviews, recompute metrics, build chart data, or put its own numbers into the PDF. If a command fails, stop.

## Current milestone

Milestone 4 is complete. `report` fetches daily pageviews and writes `pageviews.json` and `analysis.json`. `metrics.py` calculates every series number. Missing days count as zero. Unavailable days are excluded from the numerical metrics. Percent change is null, with a note, when start views are 0 or fewer than two included days exist. A constant series stores slope 0 and `r_squared` null. R² and busiest-day share have no thresholds and no trend or spike flags. Stored values are not rounded. Days after the latest returned pageview timestamp are unavailable; earlier omitted days are missing. HTTP 404 fails closed as ambiguous and never becomes zeros. The chart and the PDF are not implemented.

`resolve` loads the query title with redirects. A non-disambiguation page is the result. Search rank does not choose an article. A disambiguation page is never selected. Exact-title resolution is deterministic but can still need user clarification for queries such as `Java`.

Next, when asked: implement the chart and the one-page PDF. Do not start that work as part of milestone 4.
