# Development

## Environment

Python 3.11 or newer. This milestone has no third-party dependencies. Later chart and PDF work may add matplotlib and fpdf2; do not add them until that milestone.

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
3. Keep JSON contracts in the modules that own them: resolve request and results in `resolve.py`, series input in `report.py`, analysis shape in `analyze.py`. Inject a fake `fetch` callable when testing MediaWiki without the network.
4. Run the test command above.
5. Stop at the end of the requested milestone.

`artifacts/` is gitignored and holds later report output.

## Resolve command

```powershell
$env:PYTHONPATH = "src"
python -m wiki_interest resolve --request path\to\request.json
```

The command prints the resolve response JSON on success.
