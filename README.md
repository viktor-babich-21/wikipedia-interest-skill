# wiki-interest

An Agent Skill and a small Python package for comparing Wikipedia article pageviews across topics, languages, and time ranges. A cheap tool-using model interprets the question and explains `analysis.json`. The package resolves real article titles, calculates the metrics, draws one chart, and writes a one-page PDF.

`resolve` searches MediaWiki. `report` fetches daily pageviews and writes `pageviews.json`, `analysis.json`, `chart.png`, and `report.pdf`. The chart and the PDF are rendered from `analysis.json`.

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

## Layout

`python -m wiki_interest resolve` and `python -m wiki_interest report` are the only commands. The skill lives at `.cursor/skills/wikipedia-interest/SKILL.md`. Architecture and decisions are in `docs/`.
