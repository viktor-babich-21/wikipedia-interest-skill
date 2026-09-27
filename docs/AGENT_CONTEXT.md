# Agent context

## Product goal

Let a cheap tool-using model compare attention to Wikipedia articles across topics, language editions, and time ranges, then explain a chart and a one-page PDF whose numbers came from code.

## Boundary

The model identifies topics, languages, and dates, decides when to ask a clarifying question, chooses among `resolve` candidates, assembles `series.json` from those titles, and explains `analysis.json`.

Python owns MediaWiki search, canonical titles, langlinks, pageview fetching, day classification, every metric, the chart, the PDF, and JSON validation.

The model must not invent titles or pageviews, recompute metrics, or put its own numbers into the PDF. If a command fails, stop. The procedure is `.cursor/skills/wikipedia-interest/SKILL.md`.

## Current state

Milestones 1–6 are complete. 93 tests pass. `resolve` and `report` are the only commands.

`report` writes `pageviews.json`, `analysis.json`, `chart.png`, and one-page `report.pdf`. Metrics, the chart, and the PDF come from code. The chart and PDF read `analysis.json` and do not recalculate metrics. Missing days are 0. Unavailable days are null and are gaps on the chart. The dashed 7-day line is a visual aid and is not stored as a metric. The PDF copies stored numbers, notes, and the three fixed caveats. It has no model-written paragraph.

Percent change is null, with a note, when start views are 0 or fewer than two included days exist. A constant series stores slope 0 and `r_squared` null. R² and busiest-day share have no thresholds and no trend or spike flags. Days after the latest returned pageview timestamp are unavailable; earlier omitted days are missing. HTTP 404 fails closed and never becomes zeros.

`resolve` loads the query title with redirects. A non-disambiguation page is the result. Search rank does not choose an article. A disambiguation page is never selected. An exact title can still need a question: English `Java` is the island. There is no confidence score.

The manual review is recorded in `eval/cases.md`. On 2026-09-27, Cursor model `composer-2.5-fast` ran the six scenarios. Attempt 4 passed five and failed scenario 1, because the reply added the number 10000, which is not a field in `analysis.json`. Scenario 3 passed: the first `resolve` query was `Mercury (planet)`, and there was no second `resolve`. Preserving semantic qualifiers from the original user request is necessary because a cheap model may otherwise collapse a specific concept into a generic ambiguous title. `resolve` is expected to report `ambiguous` for `Mercury`. That earlier failure was the model shortening the user's query, not a resolver defect. There is no automated model runner. Do not start another milestone or reintroduce removed features unless the user asks.
