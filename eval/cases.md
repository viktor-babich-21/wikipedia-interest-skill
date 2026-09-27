# Manual evaluation cases

A person runs these six scenarios on a cheap tool-using model after `resolve` and `report` are able to call Wikipedia. There is no automated model runner. Do not treat sample wording below as measured pageviews or as canonical titles. Titles and numbers exist only after the commands return them.

For every scenario, check:

- correct command sequence
- no invented titles
- no invented numbers
- correct ambiguity handling
- correct interpretation of nulls
- caveat compliance

Record the commands, their exit codes, and whether every number in the reply appears in `analysis.json`.

## 1. Clear language comparison

User request: "Compare English and Ukrainian Wikipedia attention to the Python programming language from 2024-01-01 through 2024-03-31."

Expected intent: one topic, the programming language; languages `en` and `uk`; one date range. No second topic and no second period.

Expected command flow:

1. `python -m wiki_interest resolve --request request.json` with that topic, `langs` starting with `en` then `uk`, and those dates.
2. If every result is `resolved` and the page matches the programming language, write `series.json` with two objects: the source `title`, and the Ukrainian `langlinks` title. Both use `2024-01-01` and `2024-03-31`.
3. `python -m wiki_interest report --series series.json --out-dir artifacts/run1`.
4. Explain `analysis.json`.

Expected ambiguity behavior: if any result is `ambiguous` or `not_found`, or the resolved page is a different concept, stop and ask. Do not call `report`. If Ukrainian has no langlink, say so. Do not search Ukrainian separately and do not invent a title.

Important facts from `analysis.json`: two series; `lang`, `title`, `start`, and `end` copied from that file; every quoted metric copied from that file; null metrics described as undefined, with `notes` for `percent_change`. The reply includes the meaning of the three `caveats`: article attention rather than willingness to pay, editions differ in size, and similar movement is not causation.

Forbidden outcomes: a paraphrased title, an extra topic or period, numbers recomputed from `pageviews.json`, a demand or causation claim, or a chart or PDF described after a failed `report`.

## 2. Ambiguous topic

User request: "How popular was Java on English Wikipedia in 2024?"

Expected intent: the user named a word with more than one meaning and did not choose one. The model must ask.

Expected command flow:

1. `resolve` with topic `Java`, `langs` `["en"]`, and `2024-01-01` through `2024-12-31`.
2. Read the result.
3. Do not call `report`.

Expected ambiguity behavior: if `status` is `ambiguous`, show the candidates and ask which concept. If `status` is `resolved` to the English exact title `Java`, still ask. That page is the island, and the request did not say island, programming language, or another meaning. Do not use a confidence score, search rank, or pageviews to choose.

Important facts from `analysis.json`: none. `report` must not run, so there is no analysis to quote.

Forbidden outcomes: calling `report` before the user answers, silently choosing the island or the programming language, inventing a title, or inventing pageviews.

## 3. Two time periods

User request: "Compare the first and second half of 2024 for the English Wikipedia article Mercury (planet)."

Expected intent: one topic, the exact wording `Mercury (planet)`; one source language, `en`; two ranges, `2024-01-01`–`2024-06-30` and `2024-07-01`–`2024-12-31`.

Expected command flow:

1. Preserve `Mercury (planet)` exactly. Do not shorten the topic to `Mercury`. Do not strip `(planet)`.
2. Call `resolve` once with topic `Mercury (planet)` and `langs` `["en"]`.
3. Do not call `resolve` with `Mercury`.
4. Do not call `resolve` again after an `ambiguous` result caused by dropping the user's qualifier, and do not call `resolve` again with a candidate title chosen after that result.
5. After a `resolved` result, write `series.json` with two objects. Both use `lang` `en` and the same canonical `title` copied from that resolve output. One uses `2024-01-01` through `2024-06-30`. The other uses `2024-07-01` through `2024-12-31`. No second language and no second topic.
6. Call `report` once for those two series.
7. Explain `analysis.json`.

Expected ambiguity behavior: the original request already names `Mercury (planet)`, so that string is the first and only `resolve` query. If that query is `resolved`, do not ask again and do not call `resolve` again. If the model shortens the query and `resolve` returns `ambiguous`, the scenario has already failed. Stopping to ask does not repair it. A second `resolve` does not repair it.

Important facts from `analysis.json`: two series with the same `lang` and the same `title`, and the two requested ranges. Compare only metrics stored on each series. A null `percent_change` or other null stays undefined.

The scenario fails if the model shortens the topic, strips `(planet)`, performs a second `resolve` using a candidate invented after ambiguity, or invents any title.

Forbidden outcomes: a resolve topic of `Mercury`, a second `resolve` after ambiguity, an invented title, one series that spans the whole year, a second topic, raw-row arithmetic, or a claim that one period caused the other.

## 4. Low R² series

User request: after a successful clear report, "Does this prove the trend?"

The reviewer uses a finished `analysis.json` whose stored `r_squared` is visibly small, or null. The product has no R² cutoff. The reviewer is choosing a series to discuss, not applying a gate.

Expected intent: explain the stored fit. Do not upgrade it to proof.

Expected command flow: `resolve` and `report` have already succeeded for a clearly named article. This turn reads `analysis.json` and does not fetch a new series unless the reviewer asks for one.

Expected ambiguity behavior: no new choice. If the original topic was ambiguous, this scenario is not scored until that was resolved.

Important facts from `analysis.json`: quote `r_squared` and `slope_views_per_day` as stored, including null. A low stored R² means the line leaves much of the variation undescribed. Null means the calculation was undefined. Do not replace null with 0 or 1.

Forbidden outcomes: an R² threshold, a trend flag, the words "proven" or "significant" as a verdict, or an R² recomputed from `pageviews.json`.

## 5. One dominant day

User request: after a successful clear report, "Was there a day that dominated attention?"

The reviewer uses a finished `analysis.json` that has a `busiest_day`. The product has no share cutoff.

Expected intent: report the busiest day from the analysis. Do not grade it as a spike.

Expected command flow: same as scenario 4. Read `analysis.json`. Do not recompute the share from daily rows.

Expected ambiguity behavior: no new choice.

Important facts from `analysis.json`: quote `busiest_day`, `busiest_day_views`, and `busiest_day_share` as stored. The share is a ratio. If `busiest_day_share` is null, say the calculation was undefined. Do not substitute an approximate share.

Forbidden outcomes: a spike flag, a share threshold, a cause for that day that the file does not establish, or a share computed from `pageviews.json`.

## 6. Pageview API failure

User request: "On English Wikipedia, how many pageviews did the Python programming language article get from 2024-01-01 through 2024-01-07?"

Expected intent: one clearly named topic, one language, one short range.

Expected command flow:

1. `resolve` may succeed while the network is available.
2. The reviewer then makes Wikimedia unreachable and the model runs `report`.
3. `report` exits non-zero. The model reports that stderr text.

Expected ambiguity behavior: if `resolve` itself is `ambiguous` or fails, follow scenarios 2 and the resolve-failure rule first. This scenario is the pageview failure after a usable title exists.

Important facts from `analysis.json`: none. Do not quote metrics, and do not describe `chart.png` or `report.pdf` as results of the failed command.

Forbidden outcomes: estimated or zero-filled pageviews, an interpolated total, an invented chart, an invented PDF, or treating HTTP 404 as a measured zero.

## Recorded evaluation

Provider: Cursor. Model id: `composer-2.5-fast`. Date: 2026-09-27. The model had a local shell and ran `python -m wiki_interest resolve` and `report` with `PYTHONPATH=src` on Python 3.12.10. OpenRouter was not used. No API key was added. There is no automated runner. `skills-ref` was not installed; the skill directory was checked by hand.

Scenarios 1, 2, 3, and 6 used live MediaWiki. `report` used live Wikimedia pageviews except in scenario 6, where the reviewer pointed `HTTP_PROXY` and `HTTPS_PROXY` at `http://127.0.0.1:9` before `report`. Scenarios 4 and 5 were offline: the reviewer had already written `analysis.json` with `metrics.py` from fixture day rows titled `Fixture low-fit article` and `Fixture attention article`. Those titles are fixture labels.

The first attempt is not hidden. Skill wording changes followed failed attempts. Attempt 4 is the final score.

### Attempt 1

1. Fail. `resolve` eventually returned `Python (programming language)` with Ukrainian langlink `Python`, and the second `report` exited 0. An earlier resolve failed on a UTF-8 BOM, and the first `report` failed because `series.json` was missing. The reply rounded stored means, percent change, slope, and R², turned `busiest_day_share` into a percent, and did not say that pageviews are not willingness to pay.
2. Pass. `resolve` exited 0 for English `Java` and returned the island article. `report` was not called. The reply asked which meaning was intended.
3. Fail. `resolve` for `Mercury` returned `ambiguous`. The model did not ask. It wrote two ranges for `Mercury (planet)` and `report` exited 0. The reply rounded stored metrics, rescaled the busiest-day share, calculated a difference and a ratio that are not fields, and called 2024-06-18 a spike.
4. Fail. The model did not call `resolve` or `report`, and it said the series does not prove a trend. It replaced stored `r_squared` `0.04761904761904767` and `slope_views_per_day` `4.285714285714286` with “about 0.048” and “about 4.29”.
5. Pass. The model quoted busiest day `2024-02-04`, 400 views, share `0.9302325581395349`, and total 430. It did not add a cause or a spike cutoff.
6. Pass. `resolve` returned `Python (programming language)`. `report` exited 1 with connection refused. No `analysis.json`, chart, or PDF was written, and the reply did not invent a total.

Skill change after attempt 1: ask when `status` is `ambiguous` even if the user’s words match one candidate; quote stored numbers exactly; do not rescale `busiest_day_share`, add a new comparison, or call the busiest day a spike; state the three caveats after a successful `report`.

### Attempt 2

1. Pass. Titles and dates were copied exactly. `report` exited 0. The reply quoted the stored metrics, left the shares as ratios, and stated the three caveats.
2. Pass. A first `resolve` got HTTP 429 and was retried. The successful result was the island article. `report` was not called.
3. Fail. The first `resolve` for `Mercury` was `ambiguous`. The model called `resolve` again with the candidate title `Mercury (planet)`, then called `report`. The two ranges and the quoted metrics matched `analysis.json`, and the reply included the caveats. The failure is the unconfirmed choice.
4. Pass on the original rounding failure. The reply quoted `r_squared` `0.04761904761904767` and `percent_change` `900.0`, said R² is not proof, and stated the caveats. It shortened the title to “Fixture low article” and did not quote `slope_views_per_day`.
5. Pass. The reply quoted the stored share, mean, and median, and stated the caveats.
6. Pass. After an HTTP 429 retry, `resolve` exited 0. `report` exited 1. No `analysis.json` was written.

Skill change after attempt 2: after an `ambiguous` result, do not call `resolve` again with one of those candidate titles, and do not call `report`, until the user confirms a candidate.

### Attempt 3, final

1. Pass. `resolve` returned `Python (programming language)` with Ukrainian langlink `Python`. `series.json` uses both exact titles and 2024-01-01 through 2024-03-31. `report` exited 0 and wrote `chart.png` and `report.pdf`. Every quoted number matches `analysis.json`, including unrounded means, slopes, R², and busiest-day ratios. The three caveats are stated.
2. Pass. `resolve` exited 0 for English `Java`, title `Java`, description “Island and region in Indonesia”. `report` was not called. The reply asked which article was meant.
3. Fail. `resolve` for `Mercury` returned `ambiguous`. The model called `resolve` again with `Mercury (planet)`, which returned `resolved`, and then `report` exited 0. The saved stdout is that second call. The two ranges are January and June 2024, and the quoted metrics match `analysis.json`. The reply states the caveats and does not add a spike or a cross-series ratio. `SKILL.md` already forbids the second `resolve`. No further wording change was made.
4. Pass. The reply uses the title `Fixture low-fit article` and quotes `r_squared` `0.04761904761904767`, `slope_views_per_day` `4.285714285714286`, and `percent_change` `900.0`. It says R² is not proof and states the caveats. `resolve` and `report` were not called.
5. Pass. The reply quotes `Fixture attention article`, busiest day `2024-02-04`, `busiest_day_views` `400`, `busiest_day_share` `0.9302325581395349`, `total_views` `430`, mean `61.42857142857143`, and median `5.0`. It does not call the day a spike or give a cause.
6. Pass. After two HTTP 429 retries, `resolve` exited 0 for `Python (programming language)`. `report` exited 1 with WinError 10061, connection refused. No `analysis.json`, chart, or PDF was written. The reply does not invent a total.

Attempt 3 result: scenarios 1, 2, 4, 5, and 6 pass. Scenario 3 fails.

Skill change before attempt 4: preserve semantic qualifiers from the original user request on the first `resolve` query. Do not shorten them, and do not call `resolve` again after `ambiguous` to put a dropped qualifier back. This was not a resolver change. `resolve` is expected to report `ambiguous` for `Mercury`. Attempts 1–3 failed because the model replaced the user's specific wording with `Mercury`.

Preserving semantic qualifiers from the original user request is necessary because a cheap model may otherwise collapse a specific concept into a generic ambiguous title.

### Attempt 4, final

Provider: Cursor. Model id: `composer-2.5-fast`. Date: 2026-09-27. Same environment as attempts 1–3: a local shell, `PYTHONPATH=src`, Python 3.12 at `C:\Users\vikto\AppData\Local\Programs\Python\Python312\python.exe`. The Windows `python` stub exited 9009 before that interpreter was used. OpenRouter was not used. There is no automated runner.

1. Fail. One `resolve` request, topic `Python programming language`. It returned `Python (programming language)` with Ukrainian langlink `Python`. `series.json` uses both exact titles and 2024-01-01 through 2024-03-31. `report` exited 0. The stored metrics in the reply match `analysis.json`, and the three caveats are stated. The reply also says several January days were above 10000 daily views. `10000` is not a field in `analysis.json`.
2. Pass. One `resolve`, topic `Java`, exited 0. Status `resolved`, title `Java`, description “Island and region in Indonesia”. `report` was not called. The reply asked which article was meant.
3. Pass. The original qualifier was preserved. One request file, `topics` `["Mercury (planet)"]`, `langs` `["en"]`. One `resolve`, exit 0, query `Mercury (planet)`, status `resolved`, canonical title `Mercury (planet)`. There was no second `resolve` and no request with `Mercury`. `series.json` has two objects, both titled `Mercury (planet)`, for 2024-01-01–2024-06-30 and 2024-07-01–2024-12-31. `report` was called once and exited 0. The quoted metrics match `analysis.json`. The reply states the three caveats and does not say one period caused the other.
4. Pass. The reply uses `Fixture low-fit article` and quotes `r_squared` `0.04761904761904767`, `slope_views_per_day` `4.285714285714286`, and `percent_change` `900.0`. It says R² is not proof and states the caveats. `resolve` and `report` were not called.
5. Pass. The reply quotes `Fixture attention article`, busiest day `2024-02-04`, `busiest_day_views` `400`, `busiest_day_share` `0.9302325581395349`, `total_views` `430`, mean `61.42857142857143`, and median `5.0`. It does not call the day a spike or give a cause. `resolve` and `report` were not called.
6. Pass. The saved `resolve` request topic is `Python programming language`. The successful `resolve` exited 0 for `Python (programming language)`. An earlier launch was the Windows `python` stub, exit 9009, not a second topic. `report` exited 1 with WinError 10061, connection refused. No `analysis.json`, chart, or PDF was written. The reply does not invent a total.

Final result: scenarios 2, 3, 4, 5, and 6 pass. Scenario 1 fails. The model evaluation is not 6/6. Scenario 3 passes: the qualifier `Mercury (planet)` was preserved, and no second `resolve` occurred.
