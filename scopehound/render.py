"""Render results as human-readable text or stable JSON.

The JSON schema is considered part of the public interface; see the README.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from . import __version__
from .classify import MatchResult
from .model import Disposition, ParseIssue, ScopeEntry
from .overlap import Overlap

_DISPOSITION_SIGIL = {
    Disposition.IN_SCOPE: "+",
    Disposition.OUT_OF_SCOPE: "-",
    Disposition.UNKNOWN: "?",
}


def _entry_dict(entry: ScopeEntry) -> Dict:
    return {
        "kind": entry.kind.value,
        "value": entry.value,
        "exclude": entry.exclude,
        "source": entry.source,
    }


def _issue_dict(issue: ParseIssue) -> Dict:
    return {"raw": issue.raw, "reason": issue.reason, "source": issue.source}


# --- normalize ---------------------------------------------------------------

def normalize_json(entries: Sequence[ScopeEntry], issues: Sequence[ParseIssue]) -> Dict:
    in_scope = [e for e in entries if not e.exclude]
    out_scope = [e for e in entries if e.exclude]
    return {
        "tool": "scopehound",
        "version": __version__,
        "command": "normalize",
        "entries": [_entry_dict(e) for e in entries],
        "errors": [_issue_dict(i) for i in issues],
        "summary": {
            "total": len(entries),
            "in_scope": len(in_scope),
            "out_of_scope": len(out_scope),
            "errors": len(issues),
        },
    }


def normalize_text(entries: Sequence[ScopeEntry], issues: Sequence[ParseIssue]) -> str:
    lines: List[str] = []
    for e in entries:
        sigil = "-" if e.exclude else "+"
        lines.append(f"{sigil} {e.value}  [{e.kind.value}]")
    if issues:
        lines.append("")
        lines.append(f"{len(issues)} line(s) could not be parsed:")
        for i in issues:
            where = f"{i.source}: " if i.source else ""
            lines.append(f"  ! {where}{i.raw!r} - {i.reason}")
    in_scope = sum(1 for e in entries if not e.exclude)
    out_scope = sum(1 for e in entries if e.exclude)
    lines.append("")
    lines.append(
        f"{len(entries)} entries ({in_scope} in-scope, {out_scope} out-of-scope), "
        f"{len(issues)} error(s)"
    )
    return "\n".join(lines)


# --- match --------------------------------------------------------------------

def match_json(results: Sequence[MatchResult], issues: Sequence[ParseIssue]) -> Dict:
    counts = {d.value: 0 for d in Disposition}
    out_results = []
    for r in results:
        counts[r.disposition.value] += 1
        out_results.append(
            {
                "target": r.target.raw,
                "kind": r.target.kind.value,
                "disposition": r.disposition.value,
                "matched_rule": _entry_dict(r.matched) if r.matched else None,
            }
        )
    return {
        "tool": "scopehound",
        "version": __version__,
        "command": "match",
        "results": out_results,
        "errors": [_issue_dict(i) for i in issues],
        "summary": {
            "in_scope": counts[Disposition.IN_SCOPE.value],
            "out_of_scope": counts[Disposition.OUT_OF_SCOPE.value],
            "unknown": counts[Disposition.UNKNOWN.value],
            "errors": len(issues),
        },
    }


def match_text(results: Sequence[MatchResult], issues: Sequence[ParseIssue]) -> str:
    lines: List[str] = []
    for r in results:
        sigil = _DISPOSITION_SIGIL[r.disposition]
        rule = f"  ({r.matched.label()})" if r.matched else ""
        lines.append(f"{sigil} {r.target.raw}  {r.disposition.value}{rule}")
    if issues:
        lines.append("")
        lines.append(f"{len(issues)} target(s) could not be parsed:")
        for i in issues:
            lines.append(f"  ! {i.raw!r} - {i.reason}")
    return "\n".join(lines)


# --- overlaps -----------------------------------------------------------------

def overlaps_json(overlaps: Sequence[Overlap]) -> Dict:
    counts = {"duplicate": 0, "subsumes": 0, "conflict": 0}
    out = []
    for o in overlaps:
        counts[o.relation.value] += 1
        out.append(
            {
                "relation": o.relation.value,
                "a": _entry_dict(o.a),
                "b": _entry_dict(o.b),
                "note": o.note,
            }
        )
    return {
        "tool": "scopehound",
        "version": __version__,
        "command": "overlaps",
        "overlaps": out,
        "summary": {
            "duplicates": counts["duplicate"],
            "subsumptions": counts["subsumes"],
            "conflicts": counts["conflict"],
        },
    }


def overlaps_text(overlaps: Sequence[Overlap]) -> str:
    if not overlaps:
        return "no overlaps, duplicates or conflicts found"
    lines: List[str] = []
    for o in overlaps:
        lines.append(f"[{o.relation.value}] {o.note}")
    conflicts = sum(1 for o in overlaps if o.relation.value == "conflict")
    dupes = sum(1 for o in overlaps if o.relation.value == "duplicate")
    subs = sum(1 for o in overlaps if o.relation.value == "subsumes")
    lines.append("")
    lines.append(f"{dupes} duplicate(s), {subs} subsumption(s), {conflicts} conflict(s)")
    return "\n".join(lines)
