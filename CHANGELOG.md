# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-04

### Added
- `normalize` (alias `lint`): parse, normalize and de-duplicate a scope list,
  reporting malformed lines with their source location.
- `match`: classify concrete targets (domains or IPs) as in-scope,
  out-of-scope or unknown, with out-of-scope taking precedence. Targets can be
  passed as arguments or via `--targets-file` (`-` reads stdin).
- `overlaps`: report duplicate entries, redundant (subsumed) entries and
  conflicts where an out-of-scope rule covers in-scope surface.
- Support for domains, `*.wildcard` domains, IPv4/IPv6 addresses and CIDR
  ranges, with `!` prefix or a dedicated `-x/--out-of-scope` file for
  exclusions.
- Human-readable output by default and a stable `--json` schema.
- Exit codes `0` (clean), `1` (findings) and `2` (usage error).
- No network access of any kind: all analysis is offline.

[Unreleased]: https://github.com/vvs1off/scopehound/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vvs1off/scopehound/releases/tag/v0.1.0
