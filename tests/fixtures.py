"""Small, deterministic scope fixtures used by the tests."""

SCOPE_BASIC = """\
# in-scope surface
*.example.com
example.com
app.example.com
10.0.0.0/24
192.168.1.10

# carve-outs
!admin.example.com
!10.0.0.5
"""

SCOPE_WITH_ERRORS = """\
good.example.com
not a domain
*.*.bad
1.2.3.4/33
!
2001:db8::/32
"""

SCOPE_REDUNDANT = """\
*.example.com
app.example.com
*.api.example.com
10.0.0.0/16
10.0.0.0/24
10.0.0.0/24
"""

# An out-of-scope rule broader than an in-scope one is a real conflict:
# part of the declared in-scope surface is actually excluded.
SCOPE_CONFLICT = """\
app.example.com
!*.example.com
10.0.0.5
!10.0.0.0/24
dup.example.com
!dup.example.com
"""
