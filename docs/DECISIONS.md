# Decisions

## Case requirements

The case requires an Agent Skill that compares Wikipedia article attention across topics, languages, and time, resolves real pages, handles ambiguous topics, fetches pageviews, calculates metrics in code, draws a chart, and writes a concise one-page PDF. Tests include fixtures and a manual cheap-model review. The model explains results and does not invent titles or numbers.

## Implementation choices

These are our choices. The case does not name the parameter values.

### agent=user

Pageviews are requested with `agent=user` so the series counts human readers. Spider and automated traffic is a different question. The case asks for interest, and this parameter is how the Wikimedia API separates human traffic.

### access=all-access

`access=all-access` sums desktop and mobile. The case does not ask for a device split, so one access value keeps a single definition of article attention.

### Daily granularity

Daily rows make a busiest day and a moving-average line possible. Monthly mode is out of scope. The 7-day line is a chart aid, not a summary metric.

### Langlinks

The case requires the same topic to keep its own title in each language edition, and it forbids silently binding a different article. MediaWiki search, redirect resolution, and langlinks do that. Wikidata is not used. A language with no langlink is recorded as `missing langlink: <lang>`.

### Deterministic calculations

The case requires code to compute the numbers. `analysis.json` is the only source the model may quote. The PDF is rendered from that file. Quality thresholds on R², coverage, or spike share are not part of the case and are not used.

### Date floor

Requests that start before 2015-07-01 are rejected. That is the first day of the current pageview definition. Earlier pagecounts are a different metric.

### Fail closed

HTTP and JSON failures stop the command. The pipeline does not invent titles or estimate missing values. A failed pageview request does not become zero, an estimate, or an interpolated value. The `report` command exits non-zero and does not write `pageviews.json`.

### Resolve selection

The query is loaded with MediaWiki `redirects=1`. If that page exists and is not a disambiguation page, it is the result, including when the page is a redirect to a canonical title. Search is used only when that page is missing or is a disambiguation page. Search uses `list=search` in namespace 0 only. Disambiguation hits are dropped. One remaining article resolves, several become `ambiguous`, and none become `not_found`.

Search order is not a selection signal. The first search hit does not win because it is first. On 2026-09-26 the English titles `Python` and `Mercury` were both disambiguation pages, and search ranked a specific article ahead of other meanings. Those queries stay `ambiguous`. A clear query still resolves when the exact title is a non-disambiguation page, which is how a redirect such as the fixture title `Python` can resolve to `Python (programming language)` even if another concept is ranked first.

Pageviews are never used to pick a candidate. Canonical titles are copied from MediaWiki. Titles for other requested languages are copied from `langlinks` only.

Exact-title resolution is deterministic, but it can still need user clarification. Example: the English title `Java` is the island article. A user asking about "Java" may mean the programming language. There is no confidence score and no popularity ranking. The agent should confirm intent when the exact title is semantically ambiguous relative to the user's question.

### Pageview request

`report` calls the Wikimedia REST endpoint:

`/metrics/pageviews/per-article/{lang}.wikipedia/all-access/user/{title}/daily/{start}/{end}`

The path uses the `agent=user`, `access=all-access`, and daily choices above. The series title is copied into the URL with spaces turned into underscores and the segment percent-encoded. `report` does not search or resolve that title again. The title written to `pageviews.json` stays the `series.json` title even if the response names the article differently.

The same identifying User-Agent as MediaWiki is sent, with a 30-second timeout. There is no new HTTP library.

### Pageview retries

429 and HTTP 500-599 are retried. The limit is three attempts total, with a fixed one-second pause between attempts and no jitter. Timeout, malformed JSON, an unexpected response shape, and any other non-404 HTTP status fail on the first response. After the retry limit, the series and the command fail.

### Pageview HTTP 404

Wikimedia documents that a pageviews 404 can mean either zero pageviews or data not yet loaded, and the API cannot always distinguish those cases. This MVP does not treat every 404 as an ordinary transport failure, and it does not convert a 404 into observed zeros.

Conservative behavior: the series and `report` fail with an explicit ambiguity error. No `pageviews.json` is written. No zeros, estimates, or interpolated values are invented. An all-zero series is accepted only from HTTP 200 with an empty `items` array, or from explicit numeric zeros in returned rows. An explicit 0 in a row is `observed`.

### Missing and unavailable days

The per-article response does not say why a date is absent. It omits zero-view days, and it also omits days that are not published yet. Wikimedia says data is usually loaded within hours, but delays can be 24 hours or more, so a fixed `today - 2 days` lag is not treated as an API rule.

Implementation heuristic when the response contains at least one row:

- The latest returned timestamp is the published-through boundary.
- A numeric row is `observed`.
- An omitted date on or before that boundary is `missing` with `views: 0`.
- A requested date after that boundary is `unavailable` with `views: null`.

When HTTP 200 returns empty `items`, there is no returned boundary. The whole requested range is treated as `missing` with views 0. That is how this MVP records an all-zero published series. It is not claimed to be an API-labeled zero.

This boundary rule is a client heuristic, not an API guarantee.

### Metrics

`metrics.py` is the only place that calculates series numbers. `analyze.py` calls it and checks the `analysis.json` shape. `report` writes `pageviews.json` and `analysis.json`, then `chart.png` and one-page `report.pdf` from that analysis file. The chart and the PDF do not recalculate metrics. `artifacts.chart` and `artifacts.pdf` name those files.

Included days are `observed` and `missing`. `unavailable` days are excluded from total, mean, median, start, end, percent change, slope, R², and the busiest day. Missing days contribute 0. Status values are not reinterpreted. The normalized day list is chronological, so start and end views are the first and last included rows.

`days_expected` is the inclusive calendar length from `start` through `end`. The three status counts are taken from the day list and must sum to `days_expected`. A series that does not is rejected.

`total_views` sums observed counts. Missing days add 0. Unavailable days are not in the sum.

`mean_daily_views` and `median_daily_views` use included days only. An even count uses the arithmetic mean of the two central values after sorting. Both are null when no included day exists.

`percent_change` is `(end_views - start_views) / start_views * 100`. It is null when `start_views` is 0 or fewer than two included days exist. `notes` records which arithmetic case applied. Fewer-than-two is recorded when both would apply. This is not a quality threshold.

`slope_views_per_day` is the ordinary least-squares slope of included views against x = 0, 1, 2, ... in included-day order. Unavailable days are omitted from x. They are not gaps in the index. The slope is null when fewer than two included days exist. There is no minimum slope and no minimum R².

`r_squared` is the coefficient of determination of that same line. It is null when fewer than two included days exist, and when the included values are constant. A constant series has slope 0, because a horizontal line fits, but the total sum of squares is 0, so R² is undefined. The JSON value is null, never 0, 1, or NaN. R² is not classified and does not set `trend_allowed` or any strong, weak, or significant flag.

`busiest_day` is the included date with the highest views. Ties use the earliest date. `busiest_day_share` is `busiest_day_views / total_views`, a ratio, and is null when `total_views` is 0. There is no spike threshold and no spike flag.

Calculations use the Python standard library. Values are stored at full float precision. The PDF formats them for display and does not replace the stored numbers. The display rule is in `docs/ARCHITECTURE.md`.

