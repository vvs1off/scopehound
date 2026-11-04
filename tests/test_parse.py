from scopehound.model import EntryKind, ParseIssue, Target
from scopehound.parse import normalize_host, parse_entry, parse_scope_lines, parse_target

from .fixtures import SCOPE_BASIC, SCOPE_WITH_ERRORS


def test_normalize_host_strips_url_parts():
    assert normalize_host("https://App.Example.com:8443/login?x=1") == "app.example.com"
    assert normalize_host("user@host.example.com.") == "host.example.com"
    assert normalize_host("[2001:db8::1]:443") == "2001:db8::1"


def test_parse_entry_kinds():
    assert parse_entry("example.com").kind == EntryKind.DOMAIN
    assert parse_entry("*.example.com").kind == EntryKind.WILDCARD
    assert parse_entry("10.0.0.5").kind == EntryKind.IP
    assert parse_entry("10.0.0.0/24").kind == EntryKind.CIDR


def test_parse_entry_exclude_prefix():
    entry = parse_entry("!admin.example.com")
    assert entry.exclude is True
    assert entry.value == "admin.example.com"


def test_parse_entry_comments_and_blank():
    assert parse_entry("") is None
    assert parse_entry("   # a comment") is None
    assert parse_entry("example.com  # inline").value == "example.com"


def test_parse_entry_cidr_host_bits_normalized():
    entry = parse_entry("10.0.0.5/24")
    assert entry.kind == EntryKind.CIDR
    assert entry.value == "10.0.0.0/24"


def test_parse_entry_errors():
    assert isinstance(parse_entry("not a domain"), ParseIssue)
    assert isinstance(parse_entry("*.*.bad"), ParseIssue)
    assert isinstance(parse_entry("1.2.3.4/33"), ParseIssue)
    assert isinstance(parse_entry("!"), ParseIssue)


def test_parse_scope_lines_counts():
    entries, issues = parse_scope_lines(SCOPE_BASIC.splitlines(), source="scope")
    assert len(entries) == 7
    assert len(issues) == 0
    excludes = [e for e in entries if e.exclude]
    assert {e.value for e in excludes} == {"admin.example.com", "10.0.0.5"}


def test_parse_scope_lines_collects_errors():
    entries, issues = parse_scope_lines(SCOPE_WITH_ERRORS.splitlines(), source="s")
    assert len(entries) == 2
    assert len(issues) == 4
    assert issues[0].source == "s:2"


def test_force_exclude():
    entries, _ = parse_scope_lines(["a.example.com"], force_exclude=True)
    assert entries[0].exclude is True


def test_parse_target_rejects_ranges_and_wildcards():
    assert isinstance(parse_target("10.0.0.0/24"), ParseIssue)
    assert isinstance(parse_target("*.example.com"), ParseIssue)


def test_parse_target_ok():
    t = parse_target("App.Example.com")
    assert isinstance(t, Target)
    assert t.kind == EntryKind.DOMAIN
    assert t.domain == "app.example.com"
    ip = parse_target("10.0.0.5")
    assert ip.kind == EntryKind.IP
