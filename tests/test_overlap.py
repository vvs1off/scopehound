from scopehound.overlap import Relation, find_overlaps
from scopehound.parse import parse_scope_lines

from .fixtures import SCOPE_CONFLICT, SCOPE_REDUNDANT


def _entries(text):
    entries, _ = parse_scope_lines(text.splitlines(), source="s")
    return entries


def _rel(overlaps, relation):
    return [o for o in overlaps if o.relation == relation]


def test_redundant_has_no_conflicts():
    overlaps = find_overlaps(_entries(SCOPE_REDUNDANT))
    assert _rel(overlaps, Relation.CONFLICT) == []


def test_duplicate_detected_once():
    overlaps = find_overlaps(_entries(SCOPE_REDUNDANT))
    dupes = _rel(overlaps, Relation.DUPLICATE)
    assert len(dupes) == 1
    assert dupes[0].a.value == "10.0.0.0/24"


def test_subsumption_detected():
    overlaps = find_overlaps(_entries(SCOPE_REDUNDANT))
    subs = _rel(overlaps, Relation.SUBSUMES)
    covered = {o.b.value for o in subs}
    assert "app.example.com" in covered
    assert "*.api.example.com" in covered
    assert "10.0.0.0/24" in covered


def test_conflicts_detected():
    overlaps = find_overlaps(_entries(SCOPE_CONFLICT))
    conflicts = _rel(overlaps, Relation.CONFLICT)
    assert len(conflicts) >= 3
    notes = " ".join(o.note for o in conflicts)
    assert "app.example.com" in notes
    assert "10.0.0.5" in notes


def test_legit_carveout_is_not_a_conflict():
    # in-scope broad with a narrower out-of-scope carve-out is expected
    entries = _entries("*.example.com\n!secret.example.com\n")
    conflicts = _rel(find_overlaps(entries), Relation.CONFLICT)
    assert conflicts == []
