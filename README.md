# wiki-interest

An Agent Skill and a small Python package for comparing Wikipedia article pageviews across topics, languages, and time ranges. A cheap tool-using model interprets the question and explains `analysis.json`. The package resolves real article titles and, in later milestones, calculates the numbers, draws one chart, and writes a one-page PDF.

Milestone 2 implements `resolve` against MediaWiki. `report` still validates its input and stops. Pageviews, metrics, charts, and PDFs are later milestones.

## Install

Python 3.11 or newer. From the repository root:

```powershell
$env:PYTHONPATH = "src"
```

No third-party packages are required for this milestone.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

## Layout

`python -m wiki_interest resolve` and `python -m wiki_interest report` are the only commands. The skill lives at `.cursor/skills/wikipedia-interest/SKILL.md`. Architecture and decisions are in `docs/`.
