# Testing

## Unit

`tests/unit/` checks JSON contracts and helpers with no network: resolve requests with several topics, status-specific resolve results, series lists, the analysis shape, day status rules, and small resolve/langlink helpers.

## Integration

`tests/integration/` mocks MediaWiki HTTP responses for `resolve`: clear topics, multiple topics, ambiguous Mercury-like search, redirects, disambiguation, empty search, langlinks, missing langlinks, Unicode titles, and HTTP/JSON failures. Those tests must not call the live network.

## End to end

`tests/e2e/` will hold one fixture run from `series.json` through `analysis.json`, a PNG, and a PDF. It is empty until report generation exists.

## Manual evaluation

`eval/cases.md` lists six scenarios for a person to run on a cheap model after the commands work. There is no automated model runner. The reviewer checks the command trace and that every number in the chat appears in `analysis.json`.
