# Testing

## Unit

`tests/unit/` checks JSON contracts and helpers with no network: resolve requests with several topics, status-specific resolve results, series lists, the analysis shape, day status rules, and small resolve/langlink helpers.

Pageview unit tests cover day classification against the latest returned timestamp, response parsing, the pageview URL, retryable status codes, the identifying User-Agent, timeout, and malformed JSON. They mock `urlopen` or call pure functions. They do not open a socket.

## Integration

`tests/integration/` mocks MediaWiki HTTP responses for `resolve`: a clear redirect even when another concept ranks first, multiple topics, ambiguous Mercury-like search including when one concept ranks first, a disambiguation title that is not replaced by the top hit, redirects, disambiguation, empty search, langlinks, missing langlinks, Unicode titles, and HTTP/JSON failures.

Pageview integration tests mock the REST API: a successful series, several series in one input, language and period comparisons that are not expanded, an interior missing day, trailing unavailable days, a range that ends on the injected current day, an empty `items` array, 429 and 5xx retries and exhausted retries, timeout, ambiguous 404 handling that does not invent zeros, malformed JSON, a bad response shape, a start date before 2015-07-01, a Unicode title, and a parenthetical title. Those tests must not call the live network.

## End to end

`tests/e2e/` will hold one fixture run from `series.json` through `analysis.json`, a PNG, and a PDF. It is empty until report generation exists.

## Manual evaluation

`eval/cases.md` lists six scenarios for a person to run on a cheap model after the commands work. There is no automated model runner. The reviewer checks the command trace and that every number in the chat appears in `analysis.json`.

Resolve integration tests also cover exact-title `Java` resolving to the island article, documenting that deterministic title lookup can still need user clarification.
