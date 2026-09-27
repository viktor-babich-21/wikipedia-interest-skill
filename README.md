# wiki-interest

An Agent Skill and a small Python package that compare attention to Wikipedia articles across topics, languages, and time ranges. A cheap tool-using model interprets the question and explains `analysis.json`. The package resolves real article titles, fetches daily pageviews, calculates the metrics, draws one chart, and writes a one-page PDF.

`resolve` searches MediaWiki. `report` writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`. The chart and the PDF are rendered from `analysis.json`. The model does not invent titles or numbers.

## Install

Python 3.11 or newer. From the repository root:

```powershell
python -m pip install "matplotlib>=3.8,<4" "fpdf2>=2.7,<3"
$env:PYTHONPATH = "src"
```

Pageview retrieval uses the Python standard library. The chart uses matplotlib and the PDF uses fpdf2.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Unit tests do not call the network. The current suite is 93 tests.

## Workflow

1. The model writes a resolve request with the topics, languages, and dates.
2. `resolve` returns canonical titles, or `ambiguous` / `not_found`.
3. The model asks when the topic is ambiguous, then copies exact titles into `series.json`.
4. `report` writes the analysis, chart, and PDF.
5. The model explains `analysis.json`.

The procedure is `.cursor/skills/wikipedia-interest/SKILL.md`. The manual cheap-model review is recorded in `eval/cases.md`. On 2026-09-27, Cursor model `composer-2.5-fast` ran the six scenarios with a shell. The final attempt passed five and failed the ambiguous-topic stop in scenario 3. There is no automated model runner.

## Example

Compare two topics on English Wikipedia for 2024. `series.json` is written only after `resolve`, and each `title` is copied from that output:

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

```powershell
$env:PYTHONPATH = "src"
python -m wiki_interest resolve --request request.json
python -m wiki_interest report --series series.json --out-dir artifacts\run1
```

If `resolve` returns a different canonical title, that exact string replaces the sample `title`. `report` prints the `analysis.json` path. Explain that file. Do not recompute its metrics.

## MVP

- MediaWiki resolve: redirects, disambiguation pages rejected, langlinks for other editions
- Daily pageviews with `agent=user` and `access=all-access`
- Observed, missing, and unavailable days
- Per-series metrics in code, including R² and busiest-day share, with no thresholds
- `chart.png` and a one-page `report.pdf` from `analysis.json`
- A skill that stops on ambiguity and explains the analysis
- Offline unit, integration, and fixture end-to-end tests

`python -m wiki_interest resolve` and `python -m wiki_interest report` are the only commands. Architecture and decisions are in `docs/`.
