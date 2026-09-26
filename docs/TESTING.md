# Testing

## Unit

`tests/unit/` checks JSON contracts and helpers with no network: resolve requests with several topics, status-specific resolve results, series lists, the analysis shape, day status rules, and small resolve/langlink helpers.

`tests/unit/test_metrics.py` uses small hand-built day lists. It covers a normal series, missing days as zero, unavailable days excluded from the numbers and from the regression index, total, mean, median (including the even-count middle pair), start and end, percent change, percent change null when start is 0 or fewer than two included days exist, a known linear slope, R² of 1 on a perfect line, low R² on an alternating series, constant-series slope 0 with R² null and no NaN, busiest day, earliest date on a tie, busiest-day share, an all-zero series, one included day, no included days, and completeness counts. A day list whose status counts do not match the calendar length is rejected. These tests do not call the network.

Pageview unit tests cover day classification against the latest returned timestamp, response parsing, the pageview URL, retryable status codes, the identifying User-Agent, timeout, and malformed JSON. They mock `urlopen` or call pure functions. They do not open a socket.

## Integration

`tests/integration/` mocks MediaWiki HTTP responses for `resolve`: a clear redirect even when another concept ranks first, multiple topics, ambiguous Mercury-like search including when one concept ranks first, a disambiguation title that is not replaced by the top hit, redirects, disambiguation, empty search, langlinks, missing langlinks, Unicode titles, and HTTP/JSON failures.

Pageview integration tests mock the REST API: a successful series, several series in one input, language and period comparisons that are not expanded, an interior missing day, trailing unavailable days, a range that ends on the injected current day, an empty `items` array, 429 and 5xx retries and exhausted retries, timeout, ambiguous 404 handling that does not invent zeros, malformed JSON, a bad response shape, a start date before 2015-07-01, a Unicode title, and a parenthetical title. The report command test checks that a mocked fetch writes `pageviews.json`, `analysis.json`, a non-empty `chart.png`, and a non-empty `report.pdf`. Those tests must not call the live network.

## End to end

`tests/e2e/test_chart_pdf.py` builds analysis payloads from fixture day rows and renders `chart.png` and `report.pdf`. It does not call Wikimedia. The chart tests check that the file exists and is a non-empty PNG, that each series has a daily line and a 7-day line, that a missing day is y=0, that an unavailable day is a gap rather than zero, and that the 7-day line matches the mean of the included daily values. The PDF tests check that the file exists, is a non-empty one-page PDF, contains the report title, contains metric values taken from the fixture analysis, contains the three caveats, and does not contain a model-written sentence. A two-series fixture and a Cyrillic title must also render on one page.

## Manual evaluation

`eval/cases.md` lists six scenarios for a person to run on a cheap model after the commands work. There is no automated model runner. The reviewer checks the command trace and that every number in the chat appears in `analysis.json`.

Resolve integration tests also cover exact-title `Java` resolving to the island article, documenting that deterministic title lookup can still need user clarification.
