# scopehound

Passive scope validation for authorized engagements. `scopehound` parses,
normalizes and reasons about engagement scope lists — domains, wildcards, IPs
and CIDR ranges — so you can answer "is this host in scope?" before you ever
touch it.

**It never resolves, connects to or scans anything.** All analysis is offline
and based purely on the text you give it. There is no network access, no
telemetry and no third-party dependencies (Python standard library only).

```
$ scopehound match admin.example.com 10.0.0.9 8.8.8.8 --scope scope.txt
- admin.example.com  out-of-scope  (!admin.example.com)
+ 10.0.0.9  in-scope  (10.0.0.0/24)
? 8.8.8.8  unknown
```

## Why

Scope lists from a bug bounty program or a pentest statement of work are messy:
wildcards, overlapping CIDRs, duplicate hosts, and carve-outs that silently
exclude part of what looks in bounds. Testing something out of scope is how
researchers get banned or sued. `scopehound` turns that list into something you
can check a target against, and flags the contradictions before they bite.

## Install

Requires Python 3.10+.

```
git clone https://github.com/vvs1off/scopehound
cd scopehound
pip install -e .
```

This installs a `scopehound` command. Without installing you can also run it as
`python -m scopehound`.

## Scope file format

One entry per line. Blank lines and `#` comments are ignored. Entries can be:

| Form | Example | Matches |
|------|---------|---------|
| domain | `example.com` | exactly that host |
| wildcard | `*.example.com` | any sub-domain (`a.example.com`, `a.b.example.com`), **not** the apex |
| IP | `192.168.1.10` | that address (IPv4 or IPv6) |
| CIDR | `10.0.0.0/24` | any address in the range |

A leading `!` marks an entry as **out-of-scope** (a carve-out). You can also
keep exclusions in a separate file and pass it with `-x/--out-of-scope`. URLs
are accepted and reduced to their host (`https://app.example.com/login` →
`app.example.com`).

```
# scope.txt
*.example.com
example.com
10.0.0.0/24
!admin.example.com
!10.0.0.5
```

## Commands

### `normalize` (alias `lint`)

Parse, normalize and de-duplicate a list, and report lines that don't parse.

```
$ scopehound normalize scope.txt
+ *.example.com  [wildcard]
+ example.com  [domain]
+ 10.0.0.0/24  [cidr]
- admin.example.com  [domain]
- 10.0.0.5  [ip]

5 entries (3 in-scope, 2 out-of-scope), 0 error(s)
```

### `match`

Classify one or more targets. Out-of-scope always wins over in-scope, so a host
matched by a broad rule and a narrow carve-out is reported out-of-scope.

```
$ scopehound match www.example.com admin.example.com 8.8.8.8 --scope scope.txt
+ www.example.com  in-scope  (*.example.com)
- admin.example.com  out-of-scope  (!admin.example.com)
? 8.8.8.8  unknown
```

Targets can come from a file or stdin:

```
$ cat hosts.txt | scopehound match --targets-file - --scope scope.txt --json
```

### `overlaps`

Find duplicates, redundant entries and conflicts. A **conflict** is an
out-of-scope rule that covers in-scope surface — part of what you declared in
bounds is actually excluded.

```
$ scopehound overlaps scope.txt
[conflict] out-of-scope *.example.com excludes in-scope app.example.com
[conflict] out-of-scope 10.0.0.0/24 excludes in-scope 10.0.0.5

0 duplicate(s), 0 subsumption(s), 2 conflict(s)
```

## JSON output

Every command accepts `--json` and emits a stable schema. Example for `match`:

```json
{
  "tool": "scopehound",
  "version": "0.1.0",
  "command": "match",
  "results": [
    {
      "target": "admin.example.com",
      "kind": "domain",
      "disposition": "out-of-scope",
      "matched_rule": {
        "kind": "domain",
        "value": "admin.example.com",
        "exclude": true,
        "source": "scope.txt:5"
      }
    }
  ],
  "errors": [],
  "summary": { "in_scope": 0, "out_of_scope": 1, "unknown": 0, "errors": 0 }
}
```

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | success, nothing to flag |
| `1` | findings: parse errors, any out-of-scope/unknown target, or a scope conflict |
| `2` | usage error (bad arguments, missing file) |

This makes `scopehound` easy to drop into CI or a recon pipeline:

```
scopehound match "$TARGET" --scope scope.txt || { echo "refusing: not in scope"; exit 1; }
```

## Authorized use

`scopehound` is a defensive aid for people who already have written
authorization to test the systems in their scope file. It helps you stay inside
that authorization. It does not grant any access and performs no action against
any target. You are responsible for using it only against systems you are
permitted to assess.

## Development

```
pip install -e .
pip install pytest
pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
