"""Classify concrete targets against a parsed scope.

Precedence: an out-of-scope match always wins over an in-scope match, so a
target covered by both a broad in-scope rule and a narrow exclusion is reported
as out-of-scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .model import Disposition, EntryKind, ScopeEntry, Target


def entry_matches(target: Target, entry: ScopeEntry) -> bool:
    """True if ``target`` is covered by ``entry`` (ignoring exclude flag)."""

    if entry.is_ip_like:
        if target.kind != EntryKind.IP or target.address is None or entry.network is None:
            return False
        if target.address.version != entry.network.version:
            return False
        return target.address in entry.network

    if entry.is_domain_like:
        if target.kind != EntryKind.DOMAIN or target.domain is None:
            return False
        if entry.kind == EntryKind.DOMAIN:
            return target.domain == entry.domain
        # wildcard: match proper subdomains only, never the apex
        return target.domain.endswith("." + (entry.domain or ""))

    return False


@dataclass(frozen=True)
class MatchResult:
    target: Target
    disposition: Disposition
    matched: Optional[ScopeEntry]


def classify(target: Target, entries: Sequence[ScopeEntry]) -> MatchResult:
    out_match = next(
        (e for e in entries if e.exclude and entry_matches(target, e)), None
    )
    if out_match is not None:
        return MatchResult(target, Disposition.OUT_OF_SCOPE, out_match)
    in_match = next(
        (e for e in entries if not e.exclude and entry_matches(target, e)), None
    )
    if in_match is not None:
        return MatchResult(target, Disposition.IN_SCOPE, in_match)
    return MatchResult(target, Disposition.UNKNOWN, None)


def classify_all(
    targets: Sequence[Target], entries: Sequence[ScopeEntry]
) -> List[MatchResult]:
    return [classify(t, entries) for t in targets]
