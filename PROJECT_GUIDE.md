# Wikipedia Interest Skill — Project Guide

## 1. What this project is

This project is the solution for the Genesis AI Product Engineering School case.

The goal is to build an Agent Skill that lets an AI agent answer questions about Wikipedia article attention, compare topics, language editions, and time ranges, generate a chart, and produce a concise one-page PDF report.

The key engineering idea is:

> The model understands and explains the request; deterministic code retrieves the data, calculates the numbers, and generates the artifacts.

The model must not invent Wikipedia titles, pageviews, or calculated metrics.

---

## 2. Main architecture

```text
User question
    ↓
AI Agent
    ↓
resolve
    ↓
select exact resolved titles
    ↓
series.json
    ↓
report
    ↓
analysis.json
    ├── chart.png
    └── report.pdf
    ↓
AI Agent explains analysis.json
```

### AI / model responsibilities

- Understand the natural-language request.
- Identify one or more topics.
- Identify the requested Wikipedia languages.
- Identify the date range or comparison periods.
- Ask for clarification when the request is ambiguous.
- Select among candidates returned by `resolve`.
- Assemble the requested `series.json` using exact canonical titles returned by `resolve`.
- Explain verified values from `analysis.json`.

### Deterministic code responsibilities

- Search Wikipedia through the MediaWiki API.
- Resolve redirects and canonical titles.
- Retrieve interlanguage links (`langlinks`).
- Fetch daily pageviews.
- Classify missing and unavailable days.
- Calculate all numerical metrics.
- Generate the chart.
- Generate the PDF.
- Validate input/output JSON contracts.

---

## 3. Why this architecture was chosen

An LLM is useful for natural-language understanding and explanation, but it is not the right place to manually sum raw pageviews or invent article titles.

Deterministic calculations are:

- reproducible,
- testable,
- easier to debug,
- less vulnerable to hallucinated numbers.

The model therefore receives a structured `analysis.json` and explains facts that were already calculated by code.

---

## 4. Wikipedia resolution

The MVP uses:

```text
MediaWiki search
    ↓
canonical / redirect-resolved page
    ↓
langlinks
```

Wikidata is deliberately not used.

### Source language

For a request such as:

```json
{
  "topics": ["Python", "Java"],
  "langs": ["en", "uk"],
  "start": "2024-01-01",
  "end": "2024-12-31"
}
```

`langs[0]` is the source Wikipedia language.

The topics are searched in that edition. Other language titles are obtained from `langlinks` rather than by performing independent searches that could select a different concept.

### Ambiguity

The resolver must distinguish:

- one clear intended article → `resolved`
- several genuinely plausible concepts → `ambiguous`
- no relevant article → `not_found`

A disambiguation page is never accepted as the final article.

The resolver must not use pageview counts or search rank to choose a candidate. An exact non-disambiguation title resolves deterministically, but it can still need user clarification when the title is semantically ambiguous relative to the question (for example English `Java` is the island article). If that page is a disambiguation page, the remaining search hits stay ambiguous.

Canonical titles returned by `resolve` must be copied exactly into `series.json`; the model must not paraphrase or normalize them manually.

---

## 5. Pageview definition

The MVP uses:

```text
agent=user
access=all-access
granularity=daily
```

These are implementation decisions for a consistent interpretation of interest as human article attention. They are not claimed to be explicit case requirements.

The accepted start date is no earlier than `2015-07-01`.

Requests use an identifying `User-Agent`.

---

## 6. Day classification

Each requested calendar day is classified as exactly one of:

### observed

The API returned a view count.

### missing

No row was returned for a day that belongs to the published data span.

For the MVP this is treated as zero views because Wikimedia pageview time series can omit zero-value days.

### unavailable

The requested day is not yet published.

Its value is `null` and it is excluded from total, mean, median, and regression calculations.

This distinction is important: unavailable data must not silently become zero.

When the API returns at least one row, the latest timestamp is the published-through boundary: omitted earlier dates are missing (0), and later requested dates are unavailable (null). A fixed today-minus-N lag is not treated as an API rule. HTTP 404 is ambiguous and fails closed without inventing zeros. Details are in `docs/DECISIONS.md`.

---

## 7. Metrics

The MVP calculates per series:

- total views
- mean daily views
- median daily views
- start views
- end views
- percentage change
- linear slope
- R²
- busiest day
- busiest day views
- busiest day share
- expected days
- observed days
- missing days
- unavailable days

There are intentionally no:

- R² thresholds
- coverage thresholds
- spike thresholds
- `trend_allowed` flags
- forecasts
- correlations
- views-per-million normalization
- aggregate edition traffic

The actual metric values are reported rather than converted into hidden pass/fail trend gates.

Included days are `observed` and `missing`. `unavailable` days are left out of every numerical metric. Missing days contribute 0. Statuses are not reinterpreted.

`percent_change` is `(end_views - start_views) / start_views * 100`. It is null when `start_views` is 0 or fewer than two included days exist. `notes` says which of those arithmetic cases applied. If both apply, the note is the fewer-than-two case. That note is not a quality gate.

`slope_views_per_day` and `r_squared` come from one ordinary least-squares line. `x` is 0, 1, 2, ... over included days in series order, so an unavailable day is omitted rather than left as a gap in `x`. A constant series has slope 0 and `r_squared` null: a horizontal line fits, but R² divides by zero variance. The stored value is null, never NaN, 0, or 1. R² is not turned into a trend label.

`busiest_day_share` is `busiest_day_views / total_views`. Ties use the earliest date. The share is null when `total_views` is 0. There is no spike flag.

`days_expected` is the inclusive calendar length from `start` through `end`. `days_observed`, `days_missing`, and `days_unavailable` sum to `days_expected`.

An even number of included days uses the arithmetic mean of the two central values as the median.

Stored metric values keep full precision. The PDF formats them for display and does not write the rounded values back. The display rule is in `docs/ARCHITECTURE.md`.

Formulas live in `src/wiki_interest/metrics.py`. The model-facing definitions are in `.cursor/skills/wikipedia-interest/references/metrics.md`.

---

## 8. Chart and PDF

`report` writes `chart.png` and a one-page `report.pdf` after `analysis.json`. Both files are presentation. They read that JSON. They do not recalculate totals, means, slopes, shares, or any other metric, and they do not read `pageviews.json` to derive new numbers.

The chart draws the daily rows already stored on each series:

- observed days use the stored view count
- missing days are drawn as zero
- unavailable days are gaps in the line, not zeros

A dashed 7-day line is drawn on top of those daily values. For each included day it is the mean of that day and at most six preceding included days. Early days use the shorter window that exists. Unavailable days are left out of the window. The line is a visual aid. It is not a headline metric and it is not stored in `analysis.json`.

Each series is a separate color. The legend shows language and title. The daily line is solid and the average is dashed.

The PDF is one page. Its text is the report title, the dates, the article titles, the metric fields, the series notes, and the fixed caveats, plus the chart image. There is no model-written paragraph. A model explanation would be untested prose sitting next to numbers that were supposed to come only from code.

The caveats copied from `analysis.json` are:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size. These figures are article pageviews.
- Similar movement between series is not causation.

---

## 9. Testing strategy

### Unit tests

No network. Test pure logic such as validation, day classification, and metric formulas.

### Integration tests

Use mocked HTTP responses to test MediaWiki and Wikimedia API behavior.

### End-to-end test

`tests/e2e/` builds `analysis.json` from fixture day rows and checks `chart.png` and `report.pdf`. It does not call Wikimedia. The chart tests check series count, missing days as zero, unavailable days as gaps, and the 7-day line against the daily values. The PDF tests check one page, the report title, fixture metric values, the three caveats, and the absence of a model-written sentence.

### Agent evaluation

`eval/cases.md` has six scenarios a person runs on a cheap tool-using model: a clear language comparison, an ambiguous topic, two time periods, a low R² series, one dominant day, and a pageview API failure.

Review:

- command sequence
- no invented titles
- no invented numbers
- ambiguity handling
- null metrics left undefined
- caveat compliance

There is no automated model-evaluation runner. The 2026-09-27 manual run and its pass/fail record are in `eval/cases.md`.

---

## 10. Development milestones

### Milestone 1 — Project skeleton

Complete.

Included package structure, contracts, documentation, rules, and initial tests.

### Milestone 2 — Wikipedia resolver

Complete.

Implemented search, redirects, disambiguation handling, langlinks, CLI wiring, and mocked tests. Exact title lookup replaced first-hit selection during the pageview milestone.

### Milestone 3 — Pageviews

Complete.

Implemented:

- Wikimedia pageviews API
- daily data
- `agent=user`
- `access=all-access`
- date validation
- retry behavior for 429 and 5xx
- hard failure when the API cannot provide a series
- observed/missing/unavailable classification
- `pageviews.json` from the existing `report` command

Current reported state: 58 tests passing.

Corrections after the first Milestone 3 landing:
- published-through uses the latest returned pageview timestamp
- HTTP 404 fails closed with an explicit ambiguity message
- exact-title semantic ambiguity such as Java is documented and covered by a regression test

### Milestone 4 — Metrics

Complete.

Implemented in `metrics.py` and written by the existing `report` command as `analysis.json`:

- total, mean, median
- start and end views
- percent change, null when the arithmetic is undefined, with a note
- ordinary least-squares slope and R², with no threshold
- constant series: slope 0, R² null
- busiest day, views, and share, with no spike flag
- completeness counts

At the end of this milestone, `report` writes `pageviews.json` and `analysis.json`. `chart.png` and `report.pdf` are added in Milestone 5.

Current reported state: 78 tests passing.

### Milestone 5 — Chart and PDF

Complete.

`chart.py` draws `chart.png` from `analysis.json`. `pdf_report.py` draws one-page `report.pdf` from `analysis.json` and that PNG. `report` writes both after `analysis.json`. The 7-day line is visual only. The PDF copies stored metrics and the three fixed caveats. It does not contain model-written prose.

Current reported state: 93 tests passing.

### Milestone 6 — Final Skill and evaluation

Complete.

The skill at `.cursor/skills/wikipedia-interest/SKILL.md` states when it applies, the resolve → series.json → report → explain workflow, how to copy titles, when to ask, how to report failures and nulls, and the explanation limits. Metric formulas stay in `references/metrics.md`. The ambiguity example stays in `examples/ambiguous-topic.md`.

`eval/cases.md` has the six scenarios and the recorded manual run. On 2026-09-27, Cursor model `composer-2.5-fast` ran attempt 4 after the skill was told to preserve semantic qualifiers. Five scenarios passed. Scenario 1 failed because the reply added the number 10000, which is not a field in `analysis.json`. Scenario 3 passed: the first resolve query was `Mercury (planet)`, and there was no second resolve. Preserving semantic qualifiers from the original user request is necessary because a cheap model may otherwise collapse a specific concept into a generic ambiguous title. `resolve` is expected to report `ambiguous` for `Mercury`. The earlier scenario 3 failures were the model shortening the user's query, not a resolver defect. No automated model runner was added.

Test count: 93 passing.

---

## 11. Deliberately removed features

Do not reintroduce without a direct case requirement:

- Wikidata
- views per million
- aggregate edition traffic
- R²/coverage/spike thresholds
- `trend_allowed`
- narrative number checker
- caching
- automated cheap-model evaluation runner
- monthly mode
- device/geography splits
- correlation
- forecasts
- large topic × language × period matrices
- extra CLI commands
- model-written PDF prose

---

## 12. How to explain the project at the defense

The core explanation is:

> The model understands the user's request, while deterministic code performs data retrieval and numerical analysis. The model then explains the verified `analysis.json`. Charts and the PDF are generated from deterministic data, not from model-generated numbers.

Useful examples:

### Why not let the model calculate the numbers?

> Because numerical calculations are deterministic and testable. Keeping them in code makes the result reproducible and reduces hallucinated arithmetic.

### Why use MediaWiki and langlinks instead of Wikidata?

> The case requires real Wikipedia pages and language-specific titles, and MediaWiki search plus langlinks is enough for the MVP. This avoids an unnecessary second service.

### Why `agent=user`?

> We interpret interest as human article attention and therefore use the `user` traffic class consistently.

### Why stop on ambiguity?

> Choosing one interpretation silently could produce a correct-looking analysis of the wrong article. Asking the user is safer.

### Why is the PDF generated by code?

> So that the numbers in the shareable report are copied from verified deterministic output rather than being invented or reformatted by the model.

---

## 13. Current status

Milestone 1: complete.

Milestone 2: complete.

Milestone 3: complete.

Milestone 4: complete.

Milestone 5: complete.

Milestone 6: complete.

Working:

- project scaffold
- JSON contracts
- documentation aligned with the implementation
- MediaWiki resolver
- mocked resolver tests
- `resolve` command
- daily pageview fetch and day classification
- `report` writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`
- deterministic per-series metrics
- chart of daily views with a visual 7-day average
- one-page PDF from `analysis.json` and the chart
- mocked pageview tests
- fixture chart and PDF tests
- final skill procedure
- manual cheap-model evaluation recorded in `eval/cases.md` (final attempt: 5 pass, scenario 3 fail)

Current reported state: 93 tests passing. This is the final implementation milestone. The model evaluation is not 6/6.

---

## 14. Working rule for future sessions

At the beginning of a new coding session, read:

1. `docs/AGENT_CONTEXT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DECISIONS.md`
4. `.cursor/rules/wiki-interest.mdc`
5. this `PROJECT_GUIDE.md`

Then inspect the current code and tests.

Milestones 1–6 are complete. Do not start another milestone, and do not reintroduce a removed feature, unless the user asks.

After a change:

1. run all tests,
2. inspect the diff,
3. update the documentation if behavior changed,
4. update this guide's current status if the milestone state changed.

Commit only when the user asks.

The repository is the source of truth. This file is the human-readable explanation of how and why the project was built.
