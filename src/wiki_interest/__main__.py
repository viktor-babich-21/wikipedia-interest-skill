"""Command line: resolve and report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wiki_interest import ContractError
from wiki_interest.http import HttpError
from wiki_interest.pageviews import PageviewError
from wiki_interest.report import run_report
from wiki_interest.resolve import ResolveError, resolve_topics, validate_resolve_request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wiki_interest")
    commands = parser.add_subparsers(dest="command", required=True)

    resolve_cmd = commands.add_parser("resolve", help="Resolve topics to Wikipedia articles")
    resolve_cmd.add_argument("--request", required=True, help="Path to resolve request JSON")

    report_cmd = commands.add_parser(
        "report",
        help="Fetch pageviews and write analysis.json, chart.png, and report.pdf",
    )
    report_cmd.add_argument("--series", required=True, help="Path to series JSON")
    report_cmd.add_argument("--out-dir", required=True, help="Directory for report files")

    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            request = validate_resolve_request(_read_json(args.request))
            response = resolve_topics(request)
            print(json.dumps(response, ensure_ascii=False, indent=2))
            return 0
        path = run_report(_read_json(args.series), args.out_dir)
        print(path)
        return 0
    except (ContractError, ResolveError, PageviewError, HttpError, json.JSONDecodeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _read_json(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
