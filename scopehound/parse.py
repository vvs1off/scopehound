"""Parsing and normalization of scope entries and targets.

No network access happens here. URLs are reduced to their host component by
string manipulation only; nothing is resolved.
"""

from __future__ import annotations

import ipaddress
import re
from typing import List, Optional, Tuple, Union

from .model import EntryKind, ParseIssue, ScopeEntry, Target

_LABEL = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
_DOMAIN_RE = re.compile(rf"^{_LABEL}(?:\.{_LABEL})*$")


def normalize_host(raw: str) -> str:
    """Reduce a possibly URL-shaped token to a bare, lowercased host.

    Strips a scheme, any ``userinfo@``, a trailing path/query, a trailing port
    and a trailing dot. IPv6 literals may be bracketed (``[::1]:8080``).
    """

    host = raw.strip()
    if "://" in host:
        host = host.split("://", 1)[1]
    # authority ends at the first path/query/fragment separator
    for sep in ("/", "?", "#"):
        if sep in host:
            host = host.split(sep, 1)[0]
    if "@" in host:
        host = host.rsplit("@", 1)[1]
    if host.startswith("["):  # bracketed IPv6, optionally with :port
        host = host[1:].split("]", 1)[0]
    elif host.count(":") == 1:  # host:port (not a bare IPv6 literal)
        host = host.rsplit(":", 1)[0]
    return host.rstrip(".").lower()


def _classify_domain(host: str) -> Tuple[EntryKind, str, str]:
    """Return (kind, canonical_value, parent_domain) for a domain/wildcard host.

    Raises ValueError if the host is not a valid domain or wildcard.
    """

    if host.startswith("*."):
        parent = host[2:]
        if not parent or "*" in parent or not _DOMAIN_RE.match(parent):
            raise ValueError("invalid wildcard domain")
        return EntryKind.WILDCARD, f"*.{parent}", parent
    if "*" in host:
        raise ValueError("'*' is only allowed as a leading '*.' wildcard")
    if not host or not _DOMAIN_RE.match(host):
        raise ValueError("invalid domain")
    return EntryKind.DOMAIN, host, host


def _strip_comment(line: str) -> str:
    return line.split("#", 1)[0].strip()


def parse_entry(
    line: str, source: Optional[str] = None
) -> Union[ScopeEntry, ParseIssue, None]:
    """Parse one scope line into a ScopeEntry.

    Returns None for blank/comment lines, a ParseIssue for malformed lines.
    A leading ``!`` marks the entry as out-of-scope (an exclusion).
    """

    token = _strip_comment(line)
    if not token:
        return None

    exclude = False
    if token.startswith("!"):
        exclude = True
        token = token[1:].strip()
        if not token:
            return ParseIssue(raw=line.rstrip("\n"), reason="empty exclusion", source=source)

    try:
        if "/" in token:
            net = ipaddress.ip_network(token, strict=False)
            return ScopeEntry(
                kind=EntryKind.CIDR,
                value=str(net),
                exclude=exclude,
                source=source,
                network=net,
            )
        try:
            addr = ipaddress.ip_address(token)
        except ValueError:
            addr = None
        if addr is not None:
            net = ipaddress.ip_network(f"{addr}/{addr.max_prefixlen}")
            return ScopeEntry(
                kind=EntryKind.IP,
                value=str(addr),
                exclude=exclude,
                source=source,
                network=net,
            )
        host = normalize_host(token)
        kind, value, parent = _classify_domain(host)
        return ScopeEntry(
            kind=kind,
            value=value,
            exclude=exclude,
            source=source,
            domain=parent,
        )
    except ValueError as exc:
        return ParseIssue(raw=line.rstrip("\n"), reason=str(exc), source=source)


def parse_scope_lines(
    lines: List[str], source: Optional[str] = None, force_exclude: bool = False
) -> Tuple[List[ScopeEntry], List[ParseIssue]]:
    """Parse an iterable of raw lines into entries and issues.

    ``force_exclude`` marks every parsed entry as out-of-scope; use it when the
    lines come from a dedicated out-of-scope file.
    """

    entries: List[ScopeEntry] = []
    issues: List[ParseIssue] = []
    for lineno, line in enumerate(lines, start=1):
        src = f"{source}:{lineno}" if source else None
        result = parse_entry(line, source=src)
        if result is None:
            continue
        if isinstance(result, ParseIssue):
            issues.append(result)
            continue
        if force_exclude and not result.exclude:
            result = ScopeEntry(
                kind=result.kind,
                value=result.value,
                exclude=True,
                source=result.source,
                network=result.network,
                domain=result.domain,
            )
        entries.append(result)
    return entries, issues


def parse_target(raw: str) -> Union[Target, ParseIssue]:
    """Parse a concrete target (a domain or IP). Wildcards and CIDRs are errors."""

    token = _strip_comment(raw)
    if not token:
        return ParseIssue(raw=raw, reason="empty target")
    if "/" in token:
        return ParseIssue(raw=raw, reason="a target must be a single host, not a CIDR range")
    try:
        addr = ipaddress.ip_address(token)
        return Target(raw=raw.strip(), kind=EntryKind.IP, value=str(addr), address=addr)
    except ValueError:
        pass
    host = normalize_host(token)
    if host.startswith("*."):
        return ParseIssue(raw=raw, reason="a target must be a concrete host, not a wildcard")
    try:
        kind, value, parent = _classify_domain(host)
    except ValueError as exc:
        return ParseIssue(raw=raw, reason=str(exc))
    return Target(raw=raw.strip(), kind=EntryKind.DOMAIN, value=value, domain=parent)
