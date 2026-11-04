from scopehound.classify import classify, entry_matches
from scopehound.model import Disposition, EntryKind
from scopehound.parse import parse_entry, parse_scope_lines, parse_target

from .fixtures import SCOPE_BASIC


def _scope():
    entries, _ = parse_scope_lines(SCOPE_BASIC.splitlines(), source="scope")
    return entries


def _d(target):
    return classify(parse_target(target), _scope()).disposition


def test_wildcard_matches_subdomain_not_apex():
    wildcard = parse_entry("*.example.com")
    assert entry_matches(parse_target("a.example.com"), wildcard) is True
    assert entry_matches(parse_target("a.b.example.com"), wildcard) is True
    assert entry_matches(parse_target("example.com"), wildcard) is False


def test_in_scope_domain_and_ip():
    assert _d("www.example.com") == Disposition.IN_SCOPE
    assert _d("example.com") == Disposition.IN_SCOPE
    assert _d("10.0.0.9") == Disposition.IN_SCOPE
    assert _d("192.168.1.10") == Disposition.IN_SCOPE


def test_exclusion_wins_over_inclusion():
    # admin.example.com is matched by *.example.com but carved out
    assert _d("admin.example.com") == Disposition.OUT_OF_SCOPE
    # 10.0.0.5 is inside 10.0.0.0/24 but carved out
    assert _d("10.0.0.5") == Disposition.OUT_OF_SCOPE


def test_unknown_target():
    assert _d("other.org") == Disposition.UNKNOWN
    assert _d("8.8.8.8") == Disposition.UNKNOWN


def test_domain_target_never_matches_ip_rule():
    ip_rule = parse_entry("10.0.0.0/24")
    assert entry_matches(parse_target("example.com"), ip_rule) is False


def test_matched_rule_recorded():
    result = classify(parse_target("www.example.com"), _scope())
    assert result.matched is not None
    assert result.matched.kind == EntryKind.WILDCARD
