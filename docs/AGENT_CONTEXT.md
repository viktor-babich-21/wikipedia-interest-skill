# Agent context

## Product goal

Let a cheap tool-using model compare attention to Wikipedia articles across topics, language editions, and time ranges, then explain a chart and a one-page PDF whose numbers came from code.

## Boundary

The model identifies topics, languages, and dates, decides when to ask a clarifying question, chooses among `resolve` candidates, assembles `series.json` from those titles, and explains `analysis.json`.

Python owns MediaWiki search, canonical titles, langlinks, pageview fetching, day classification, every metric, the chart, the PDF, and JSON validation.

The model must not invent titles or pageviews, recompute metrics, build chart data, or put its own numbers into the PDF. If a command fails, stop.

## Current milestone

Milestone 5 is complete. `report` fetches daily pageviews and writes `pageviews.json`, `analysis.json`, `chart.png`, and one-page `report.pdf`. `metrics.py` calculates every series number. The chart and PDF read `analysis.json` only. They do not recalculate metrics. Missing days are 0 on the chart. Unavailable days are gaps, not zeros. The dashed 7-day line is a visual aid and is not stored as a metric. The PDF copies stored numbers, notes, and the three fixed caveats. It has no model-written paragraph. Percent change is null, with a note, when start views are 0 or fewer than two included days exist. A constant series stores slope 0 and `r_squared` null. R² and busiest-day share have no thresholds and no trend or spike flags. Stored values are not rounded; the PDF has a separate display format. Days after the latest returned pageview timestamp are unavailable; earlier omitted days are missing. HTTP 404 fails closed as ambiguous and never becomes zeros.

`resolve` loads the query title with redirects. A non-disambiguation page is the result. Search rank does not choose an article. A disambiguation page is never selected. Exact-title resolution is deterministic but can still need user clarification for queries such as `Java`.

Next, when asked: Milestone 6, the final Skill and evaluation pass. Do not start that work as part of milestone 5.
