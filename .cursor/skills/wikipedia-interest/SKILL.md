---
name: wikipedia-interest
description: >-
  Compares Wikipedia article interest and pageviews over time, including
  comparisons between topics, languages, and periods, then explains a
  code-produced report. Use when the user asks about Wikipedia article
  interest, Wikipedia pageviews, interest over time, comparisons between
  topics, comparisons between languages, comparisons between periods, or a
  shareable pageview report.
---

# Wikipedia interest

Python resolves real titles, fetches daily pageviews, calculates every metric, and writes `analysis.json`, `chart.png`, and `report.pdf`. The model understands the request and explains `analysis.json`. The PDF has no model-written paragraph.

## When this applies

- Wikipedia article interest
- Wikipedia pageviews
- interest over time
- comparisons between topics
- comparisons between languages
- comparisons between periods

## Preserve the user's topic wording

When extracting a topic, preserve semantic qualifiers from the user's original request. Preserve parenthetical qualifiers. Preserve programming-language and other context qualifiers. Never shorten a specific topic into a generic ambiguous one. Never remove information the user supplied that identifies the concept.

If the original request already specifies the intended concept, pass that exact information to `resolve`. Do not invent a qualifier the user did not provide.

User: "Mercury (planet)". Correct query: "Mercury (planet)". Incorrect: "Mercury".

User: "Python programming language". Correct: "Python programming language". Incorrect: "Python".

If `resolve` returns `ambiguous`, do not call `resolve` again with a shortened, invented, or newly inferred candidate title. Do not shorten "Mercury (planet)" to "Mercury", receive `ambiguous`, and then call `resolve` again with "Mercury (planet)". Ask the user instead.

## Workflow

1. Understand the request. Copy each topic with its semantic qualifiers, as in Preserve the user's topic wording. Determine the language codes and date ranges. A period comparison keeps both ranges for step 5. Put the edition to search first in `langs`.
2. Call resolve. From the repo root, with `PYTHONPATH=src` if the package is not installed:

```powershell
python -m wiki_interest resolve --request request.json
```

Request shape. `topics` are the user's wording, including qualifiers. Do not copy the shorter titles in this shape example when the user wrote a more specific topic.

```json
{
  "topics": ["Python", "Java"],
  "langs": ["en", "uk"],
  "start": "2024-01-01",
  "end": "2024-12-31"
}
```

3. Stop and ask when any result is `ambiguous` or `not_found`, and when a resolved title does not settle a genuinely ambiguous concept. Show the candidates. Do not call `resolve` again. Do not call `report`. A phrase in the request does not select a candidate from an `ambiguous` result. Preserving a qualifier the user already wrote is the first `resolve` query, not a second call and not a choice among candidates. A disambiguation page is not a choice.
4. Copy exact canonical titles from the resolve output. Do not paraphrase them.
5. Construct `series.json`.
6. Call report:

```powershell
python -m wiki_interest report --series series.json --out-dir artifacts/run1
```

This writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`.
7. Read `analysis.json`.
8. Explain the results from that file.

If a command exits with an error, stop.

## series.json

- Copy each `title` exactly from a resolved `title` or from `langlinks[].title`. Do not paraphrase canonical titles.
- Do not independently search another language when a langlink is missing. Tell the user. A `missing langlink: <lang>` note stays missing.
- Do not create topic, language, or period combinations the user did not request.
- Preserve the user's requested date ranges.
- One object per requested series. Several topics stay several objects. Another language uses that langlink title and the same dates. Two periods repeat one title with those two ranges.

Two topics, one language, one shared range:

```json
{
  "series": [
    {
      "lang": "en",
      "title": "Python",
      "start": "2024-01-01",
      "end": "2024-12-31"
    },
    {
      "lang": "en",
      "title": "Java",
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  ]
}
```

When resolve returns a different canonical title, use that exact string in `title`.

## Ambiguity

Do not silently choose among genuinely ambiguous concepts. If `status` is `ambiguous`, ask which candidate is meant, even when one title or description matches the user's words. Do not call `resolve` again with one of those candidate titles, with a shortened title, or with a qualifier you dropped and then restored. Do not call `report` until the user confirms which candidate to use. Do not blindly trust a generic exact title when the user's intent is semantically ambiguous.

"Java" can refer to different concepts. The English exact title `Java` is the island. If the context does not make the intended meaning clear, ask before `report`.

Do not introduce confidence scores. Do not rank candidates by search order or by pageviews.

## Errors

- If resolve fails, report the actual failure. Do not invent a page.
- If resolve is ambiguous, ask for clarification. Do not call `report`.
- If report fails because Wikimedia is unavailable, report the failure. Do not estimate values. Do not invent a chart or PDF result.
- If analysis contains null metrics, explain that the calculation was undefined. Do not replace null with an approximate number. For `percent_change`, use the series `notes`.

## Explanation

Explain `analysis.json`, not raw API rows. Quote every number exactly as stored in that file. Do not round a stored number, turn `busiest_day_share` into a percent, or calculate a difference, multiple, or other figure that is not a field there. Do not call the busiest day a spike. Use the user's language when practical.

When `report` succeeded, state the three `caveats` from `analysis.json`: pageviews measure attention to the article, not willingness to pay; editions differ in size; similar movement is not causation. A reported R² is not proof. Null metrics stay undefined.

R² and busiest-day share have no threshold. A missing day and an unavailable day mean different things. Field definitions are in [references/metrics.md](references/metrics.md). Do not recompute the metrics.

The dashed 7-day line is a chart aid. It is not a field in `analysis.json`.

## Hard limits

- Never invent titles.
- Never invent numbers.
- Never recompute metrics from raw data.
- Never silently choose among genuinely ambiguous concepts.
- Never turn an API failure into a number.
- Never claim pageviews prove willingness to pay.
- Never claim a correlation or causation that the data does not establish.

## References

- Fields and metrics: [references/metrics.md](references/metrics.md)
- Ambiguous topic: [examples/ambiguous-topic.md](examples/ambiguous-topic.md)
