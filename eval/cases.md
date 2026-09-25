# Manual evaluation cases

Run these by hand on a cheap tool-using model after `resolve` and `report` call Wikipedia. This milestone does not run them. There is no automated runner.

For each case, record the commands, their exit codes, and whether every number in the reply appears in `analysis.json`.

1. Compare Python and Java on English Wikipedia for 2024. Expect two topics, one language, and a `series.json` with two titles.
2. Ask about Mercury in English and Ukrainian with no subject named. Expect `ambiguous` and a question. Expect no `report` call.
3. Compare the first quarter of 2024 with the second quarter for one chosen article. Expect the same title twice, with different dates.
4. Use a fixture or a live series whose R² is low. The reply may quote `r_squared` and must not add a cutoff of its own.
5. Use a series where one day has a large share of views. The reply may quote `busiest_day` and `busiest_day_share`.
6. Force a failed HTTP call. The reply reports the failure and does not fill in pageviews.
