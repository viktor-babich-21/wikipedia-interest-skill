# Development

## Environment

Python 3.11 or newer. Pageview retrieval uses `urllib` from the standard library. Do not add matplotlib or fpdf2 until the chart and PDF milestone.

## Install

From the repository root:

```powershell
$env:PYTHONPATH = "src"
python -c "import wiki_interest"
```

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Unit tests must pass without a network connection.

## Workflow

1. Read `docs/ARCHITECTURE.md` and `docs/AGENT_CONTEXT.md`.
2. Change one milestone at a time.
3. Keep JSON contracts in the modules that own them: resolve request and results in `resolve.py`, series input in `report.py`, pageview rows in `pageviews.py`, metric formulas in `metrics.py`, analysis shape in `analyze.py`. Inject a fake `fetch` callable when testing MediaWiki or pageviews without the network. `report` writes `pageviews.json` and `analysis.json` under `--out-dir`. It does not write the chart or PDF yet.
4. Run the test command above.
5. Stop at the end of the requested milestone.

`artifacts/` is gitignored and holds report output.

## Resolve command

```powershell
$env:PYTHONPATH = "src"
python -m wiki_interest resolve --request path\to\request.json
```

The command prints the resolve response JSON on success.

## Report command

```powershell
$env:PYTHONPATH = "src"
python -m wiki_interest report --series path\to\series.json --out-dir artifacts\run1
```

The command writes `pageviews.json` and `analysis.json`, and prints the `analysis.json` path. It does not write a chart or a PDF. A failed request exits with code 1 and does not write either file. Metric numbers in `analysis.json` are full precision.
