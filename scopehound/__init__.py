"""scopehound - passive scope validation for authorized engagements.

scopehound parses, normalizes and reasons about engagement scope lists
(domains, wildcards, IPs and CIDRs). It never resolves or contacts any target:
all analysis is offline and based purely on the text you give it.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
