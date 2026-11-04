"""Command-line interface for scopehound.

Exit codes:
  0  success, nothing to flag
  1  findings (parse errors, out-of-scope/unknown targets, or scope conflicts)
  2  usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Sequence, Tuple

from . import __version__
from . import render
from .classify import classify_all
from .model import ParseIssue, ScopeEntry, Target
from .overlap import Relation, find_overlaps
from .parse import parse_scope_lines, parse_target

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


def _read_lines(path: str) -> List[str]:
    if path == "-":
        return sys.stdin.read().splitlines()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read().splitlines()


def _load_scope(
    scope_paths: Sequence[str], oos_paths: Sequence[str]
) -> Tuple[List[ScopeEntry], List[ParseIssue]]:
    entries: List[ScopeEntry] = []
    issues: List[ParseIssue] = []
    for path in scope_paths:
        e, i = parse_scope_lines(_read_lines(path), source=path)
        entries.extend(e)
        issues.extend(i)
    for path in oos_paths:
        e, i = parse_scope_lines(_read_lines(path), source=path, force_exclude=True)
        entries.extend(e)
        issues.extend(i)
    return entries, issues


def _emit(payload_json, text: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload_json, indent=2))
    else:
        print(text)


def _cmd_normalize(args: argparse.Namespace) -> int:
    entries, issues = _load_scope(args.files, args.out_of_scope)
    _emit(
        render.normalize_json(entries, issues),
        render.normalize_text(entries, issues),
        args.json,
    )
    return EXIT_FINDINGS if issues else EXIT_OK


def _cmd_match(args: argparse.Namespace) -> int:
    entries, scope_issues = _load_scope(args.scope, args.out_of_scope)

    raw_targets: List[str] = list(args.targets)
    if args.targets_file:
        raw_targets.extend(_read_lines(args.targets_file))

    targets: List[Target] = []
    target_issues: List[ParseIssue] = []
    for raw in raw_targets:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parsed = parse_target(raw)
        if isinstance(parsed, ParseIssue):
            target_issues.append(parsed)
        else:
            targets.append(parsed)

    if not targets and not target_issues:
        print("error: no targets given (pass targets as arguments or --targets-file)", file=sys.stderr)
        return EXIT_USAGE

    results = classify_all(targets, entries)
    all_issues = scope_issues + target_issues
    _emit(
        render.match_json(results, all_issues),
        render.match_text(results, all_issues),
        args.json,
    )

    clean = all(r.disposition.value == "in-scope" for r in results)
    return EXIT_OK if (clean and not all_issues) else EXIT_FINDINGS


def _cmd_overlaps(args: argparse.Namespace) -> int:
    entries, issues = _load_scope(args.files, args.out_of_scope)
    overlaps = find_overlaps(entries)
    _emit(
        render.overlaps_json(overlaps),
        render.overlaps_text(overlaps),
        args.json,
    )
    conflicts = any(o.relation == Relation.CONFLICT for o in overlaps)
    return EXIT_FINDINGS if (conflicts or issues) else EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scopehound",
        description=(
            "Validate and reason about engagement scope lists offline. "
            "scopehound never resolves or contacts any target."
        ),
        epilog=(
            "examples:\n"
            "  scopehound normalize scope.txt\n"
            "  scopehound match app.example.com 10.0.0.5 --scope scope.txt\n"
            "  cat hosts.txt | scopehound match --targets-file - -s scope.txt --json\n"
            "  scopehound overlaps scope.txt -x out-of-scope.txt\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"scopehound {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="emit JSON instead of text")
    common.add_argument("-v", "--verbose", action="store_true", help="more detail (reserved)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_norm = sub.add_parser(
        "normalize",
        parents=[common],
        help="parse, normalize and de-duplicate a scope list",
        aliases=["lint"],
    )
    p_norm.add_argument("files", nargs="+", help="scope file(s); '-' reads stdin")
    p_norm.add_argument(
        "-x", "--out-of-scope", action="append", default=[],
        metavar="FILE", help="file whose entries are all out-of-scope",
    )
    p_norm.set_defaults(func=_cmd_normalize)

    p_match = sub.add_parser(
        "match",
        parents=[common],
        help="classify targets as in-scope / out-of-scope / unknown",
    )
    p_match.add_argument("targets", nargs="*", help="hosts or IPs to classify")
    p_match.add_argument(
        "-s", "--scope", action="append", default=[], required=True,
        metavar="FILE", help="scope file; repeatable; '-' reads stdin",
    )
    p_match.add_argument(
        "-x", "--out-of-scope", action="append", default=[],
        metavar="FILE", help="file whose entries are all out-of-scope",
    )
    p_match.add_argument(
        "--targets-file", metavar="FILE",
        help="read targets (one per line) from a file; '-' reads stdin",
    )
    p_match.set_defaults(func=_cmd_match)

    p_over = sub.add_parser(
        "overlaps",
        parents=[common],
        help="report duplicates, redundant entries and scope conflicts",
    )
    p_over.add_argument("files", nargs="+", help="scope file(s); '-' reads stdin")
    p_over.add_argument(
        "-x", "--out-of-scope", action="append", default=[],
        metavar="FILE", help="file whose entries are all out-of-scope",
    )
    p_over.set_defaults(func=_cmd_overlaps)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc.strerror}: {exc.filename}", file=sys.stderr)
        return EXIT_USAGE
    except BrokenPipeError:
        return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
