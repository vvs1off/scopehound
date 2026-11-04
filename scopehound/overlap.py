"""Detect redundancy and conflicts within a scope.

Three relations are reported:

* ``duplicate``  - two entries are identical.
* ``subsumes``   - one entry fully covers another of the same disposition,
                   so the narrower one is redundant.
* ``conflict``   - an out-of-scope entry covers an in-scope entry (or vice
                   versa), meaning part of the declared in-scope surface is
                   actually excluded.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from .model import EntryKind, ScopeEntry


class Relation(str, Enum):
    DUPLICATE = "duplicate"
    SUBSUMES = "subsumes"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class Overlap:
    relation: Relation
    a: ScopeEntry  # the broader / first entry
    b: ScopeEntry  # the narrower / second entry
    note: str


def _same_identity(a: ScopeEntry, b: ScopeEntry) -> bool:
    return a.kind == b.kind and a.value == b.value


def _covers(a: ScopeEntry, b: ScopeEntry) -> bool:
    """True if every host matched by ``b`` is also matched by ``a`` (a is broader).

    Only compares reachability, ignoring the exclude flag.
    """

    if _same_identity(a, b):
        return False

    if a.is_ip_like and b.is_ip_like:
        if a.network is None or b.network is None:
            return False
        if a.network.version != b.network.version:
            return False
        return b.network.subnet_of(a.network)

    if a.kind == EntryKind.WILDCARD and b.is_domain_like:
        parent = a.domain or ""
        base = b.domain or ""  # host for DOMAIN, parent for WILDCARD
        return base.endswith("." + parent)

    return False


def find_overlaps(entries: Sequence[ScopeEntry]) -> List[Overlap]:
    overlaps: List[Overlap] = []
    seen_dupe: set = set()

    for i, a in enumerate(entries):
        for j, b in enumerate(entries):
            if i >= j:
                continue
            if _same_identity(a, b):
                if a.exclude == b.exclude:
                    key = (a.kind, a.value, a.exclude)
                    if key in seen_dupe:
                        continue
                    seen_dupe.add(key)
                    overlaps.append(
                        Overlap(Relation.DUPLICATE, a, b, f"{a.label()} listed more than once")
                    )
                else:
                    overlaps.append(
                        Overlap(
                            Relation.CONFLICT,
                            a,
                            b,
                            f"{a.value} is listed both in-scope and out-of-scope",
                        )
                    )
                continue

            # directional coverage, both orders
            for broad, narrow in ((a, b), (b, a)):
                if not _covers(broad, narrow):
                    continue
                if broad.exclude == narrow.exclude:
                    overlaps.append(
                        Overlap(
                            Relation.SUBSUMES,
                            broad,
                            narrow,
                            f"{broad.label()} already covers {narrow.label()}",
                        )
                    )
                elif broad.exclude and not narrow.exclude:
                    overlaps.append(
                        Overlap(
                            Relation.CONFLICT,
                            broad,
                            narrow,
                            f"out-of-scope {broad.value} excludes in-scope {narrow.value}",
                        )
                    )
                # broad in-scope covering a narrow exclusion is expected
                # (a carve-out) and is not reported.

    return overlaps
