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

Stored metric values keep full precision. Rounding belongs to later presentation and must not replace the numbers in `analysis.json`.

Formulas live in `src/wiki_interest/metrics.py`. The model-facing definitions are in `.cursor/skills/wikipedia-interest/references/metrics.md`.

---

## 8. Chart and PDF

The chart eventually contains:

- daily views
- a 7-day moving average

The moving average is a visualization aid, not a headline metric.

The PDF is rendered entirely from deterministic data. It may contain:

- titles
- dates
- metric values
- chart
- notes
- fixed caveats

The MVP does not place model-written free-form prose inside the PDF.

The PDF includes these caveats:

- Page views measure attention to a Wikipedia article, not willingness to pay.
- Wikipedia editions differ in size.
- Similar movement between series is not causation.

---

## 9. Testing strategy

### Unit tests

No network. Test pure logic such as validation, day classification, and metric formulas.

### Integration tests

Use mocked HTTP responses to test MediaWiki and Wikimedia API behavior.

### End-to-end test

Use fixture responses and verify that `report` produces:

- `analysis.json`
- a non-empty chart
- a PDF with the expected fact strip and caveats

### Agent evaluation

A small manually reviewed set of scenarios is run with a cheap tool-using model.

Review:

- command choice
- ambiguity handling
- exact-title usage
- number faithfulness
- caveat compliance

There is no automated model-evaluation runner in the MVP.

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

`report` still writes `pageviews.json`. It does not write the chart or the PDF.

Current reported state: 78 tests passing.

### Milestone 5 — Chart and PDF

Implement:

- daily line
- 7-day moving average
- one-page deterministic PDF
- fixed caveats
- fixture-based end-to-end test

### Milestone 6 — Final Skill and evaluation

Finish:

- `SKILL.md`
- references
- example scenarios
- manual evaluation cases
- documentation cleanup
- final full test run

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

Working:

- project scaffold
- JSON contracts
- documentation
- MediaWiki resolver
- mocked resolver tests
- `resolve` command
- daily pageview fetch and day classification
- `report` writes `pageviews.json` and `analysis.json`
- deterministic per-series metrics
- mocked pageview tests

Not implemented:

- chart
- PDF
- final Skill and evaluation pass

Current reported state: 78 tests passing.

---

## 14. Working rule for future sessions

At the beginning of a new coding session, read:

1. `docs/AGENT_CONTEXT.md`
2. `docs/ARCHITECTURE.md`
3. `docs/DECISIONS.md`
4. `.cursor/rules/wiki-interest.mdc`
5. this `PROJECT_GUIDE.md`

Then inspect the current code and tests.

Implement only the current milestone.

After every milestone:

1. run all tests,
2. inspect the diff,
3. update the documentation,
4. update this guide's current status,
5. commit the working state.

The repository is the source of truth. This file is the human-readable explanation of how and why the project was built.
