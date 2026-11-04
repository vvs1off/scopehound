"""Core data types shared across scopehound."""

from __future__ import annotations

import ipaddress
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]
IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


class EntryKind(str, Enum):
    """The shape of a scope entry or a target."""

    DOMAIN = "domain"
    WILDCARD = "wildcard"
    IP = "ip"
    CIDR = "cidr"


class Disposition(str, Enum):
    """The result of classifying a target against a scope."""

    IN_SCOPE = "in-scope"
    OUT_OF_SCOPE = "out-of-scope"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ScopeEntry:
    """A single normalized rule from a scope list.

    ``network`` is set for IP and CIDR entries (a single IP is stored as a
    host network, e.g. ``/32``), and ``domain`` is set for DOMAIN and WILDCARD
    entries (for a wildcard it holds the parent, without the ``*.`` prefix).
    """

    kind: EntryKind
    value: str
    exclude: bool = False
    source: Optional[str] = None
    network: Optional[IpNetwork] = None
    domain: Optional[str] = None

    @property
    def is_ip_like(self) -> bool:
        return self.kind in (EntryKind.IP, EntryKind.CIDR)

    @property
    def is_domain_like(self) -> bool:
        return self.kind in (EntryKind.DOMAIN, EntryKind.WILDCARD)

    def label(self) -> str:
        return f"!{self.value}" if self.exclude else self.value


@dataclass(frozen=True)
class Target:
    """A concrete host to classify: a domain or an IP address."""

    raw: str
    kind: EntryKind  # DOMAIN or IP only
    value: str
    address: Optional[IpAddress] = None
    domain: Optional[str] = None


@dataclass(frozen=True)
class ParseIssue:
    """A line that could not be parsed."""

    raw: str
    reason: str
    source: Optional[str] = None
