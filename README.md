# wiki-interest

An Agent Skill and a small Python package for comparing Wikipedia article pageviews across topics, languages, and time ranges. A cheap tool-using model interprets the question and explains `analysis.json`. The package resolves real article titles, calculates the metrics, and, in a later milestone, draws one chart and writes a one-page PDF.

Milestone 4 implements `resolve` against MediaWiki and `report` against the pageview API. `report` writes `pageviews.json` and `analysis.json`. Charts and PDFs are later milestones.

## Install

Python 3.11 or newer. From the repository root:

```powershell
$env:PYTHONPATH = "src"
```

No third-party packages are required for this milestone. Pageviews use the Python standard library.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Layout

`python -m wiki_interest resolve` and `python -m wiki_interest report` are the only commands. The skill lives at `.cursor/skills/wikipedia-interest/SKILL.md`. Architecture and decisions are in `docs/`.
