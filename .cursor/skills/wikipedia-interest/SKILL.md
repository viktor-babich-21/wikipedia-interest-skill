---
name: wikipedia-interest
description: >-
  Compares Wikipedia article pageviews across topics, languages, and time
  ranges, then explains a code-produced one-page report. Use when the user
  asks about Wikipedia popularity, page views, article attention, interest
  over time, or a shareable pageview report.
---

# Wikipedia interest

The model understands the question and explains `analysis.json`. `resolve` looks up real Wikipedia titles through MediaWiki. `report` will calculate numbers later; it is not implemented yet.

## Workflow

1. Identify one or more topics, the language codes, and the dates. A period comparison has two ranges; record both for step 5. Put the language to search first in `langs`.
2. Write a resolve request:

```json
{
  "topics": ["Python", "Java"],
  "langs": ["en", "uk"],
  "start": "2024-01-01",
  "end": "2024-12-31"
}
```

3. Run `python -m wiki_interest resolve --request request.json` from the repo root, with `PYTHONPATH=src` if the package is not installed.
4. Stop when any result has status `ambiguous` or `not_found`. Show the candidates and ask. A disambiguation page is not a choice. Do not search another language yourself. A missing langlink stays missing.
5. After every topic is `resolved`, write `series.json` using only the returned `title` and `langlinks`. One object per line. Do not expand a topic × language × period matrix. Copy a langlink title for another language. Repeat one title with different dates for a period comparison.
6. Run `python -m wiki_interest report --series series.json --out-dir artifacts/run1`.
7. Explain `analysis.json` in the user's language. Quote its numbers. Do not recompute them.

If a command exits with an error, or `report` prints `not implemented`, stop. Do not estimate titles, pageviews, or metrics.

## Hard limits

- Do not invent a Wikipedia title.
- Do not invent pageview data.
- Do not calculate metrics from raw rows.
- Do not put model-written numbers or prose into the PDF.
- Do not continue after a failed command by filling in values.

## References

- Metric definitions: [references/metrics.md](references/metrics.md)
- Ambiguous topic: [examples/ambiguous-topic.md](examples/ambiguous-topic.md)
