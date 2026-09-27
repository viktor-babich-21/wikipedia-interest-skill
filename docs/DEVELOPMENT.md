# Development

## Environment

Python 3.11 or newer. Pageview retrieval uses `urllib` from the standard library. Chart and PDF rendering need `matplotlib` and `fpdf2`, declared in `pyproject.toml`. Do not add pandas, numpy, or another plotting or report library as a direct dependency. Matplotlib installs numpy for itself. This package does not import numpy.

## Install

From the repository root:

```powershell
python -m pip install "matplotlib>=3.8,<4" "fpdf2>=2.7,<3"
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
2. Milestones 1–6 are complete. Change behavior only when the user asks, and do not reintroduce a removed feature.
3. Keep JSON contracts in the modules that own them: resolve request and results in `resolve.py`, series input in `report.py`, pageview rows in `pageviews.py`, metric formulas in `metrics.py`, analysis shape in `analyze.py`. The chart and PDF read `analysis.json` and do not own formulas. Inject a fake `fetch` callable when testing MediaWiki or pageviews without the network. `report` writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf` under `--out-dir`.
4. Run the test command above.
5. Do not start another milestone.

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

The command writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`, and prints the `analysis.json` path. Chart and PDF generation read the written `analysis.json`. They do not recalculate metrics. A failed pageview request exits with code 1 and does not write the files. Metric numbers in `analysis.json` stay at full precision. PDF display formatting is in `docs/ARCHITECTURE.md`.

## Skill and evaluation

The model procedure is `.cursor/skills/wikipedia-interest/SKILL.md`. The cheap-model review was run by hand on 2026-09-27 and is recorded in `eval/cases.md`. This repository does not include a model runner.
