import json

from scopehound.cli import main

from .fixtures import SCOPE_BASIC, SCOPE_CONFLICT, SCOPE_WITH_ERRORS


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_normalize_clean_exit_zero(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    assert main(["normalize", scope]) == 0
    out = capsys.readouterr().out
    assert "+ example.com" in out


def test_normalize_errors_exit_one(tmp_path, capsys):
    scope = _write(tmp_path, "bad.txt", SCOPE_WITH_ERRORS)
    assert main(["normalize", scope, "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["errors"] == 4
    assert data["command"] == "normalize"


def test_match_all_in_scope_exit_zero(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    code = main(["match", "www.example.com", "10.0.0.9", "--scope", scope])
    assert code == 0


def test_match_out_of_scope_exit_one(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    code = main(["match", "admin.example.com", "-s", scope, "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["results"][0]["disposition"] == "out-of-scope"
    assert data["summary"]["out_of_scope"] == 1


def test_match_unknown_exit_one(tmp_path):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    assert main(["match", "nope.org", "-s", scope]) == 1


def test_match_no_targets_is_usage_error(tmp_path):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    assert main(["match", "-s", scope]) == 2


def test_match_targets_file(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", SCOPE_BASIC)
    targets = _write(tmp_path, "t.txt", "www.example.com\n# comment\n\nadmin.example.com\n")
    code = main(["match", "--targets-file", targets, "-s", scope, "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert len(data["results"]) == 2


def test_overlaps_conflict_exit_one(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", SCOPE_CONFLICT)
    code = main(["overlaps", scope, "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["summary"]["conflicts"] >= 3


def test_overlaps_clean_exit_zero(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", "a.example.com\nb.example.com\n")
    assert main(["overlaps", scope]) == 0
    assert "no overlaps" in capsys.readouterr().out


def test_out_of_scope_file_forces_exclude(tmp_path, capsys):
    scope = _write(tmp_path, "scope.txt", "*.example.com\n")
    oos = _write(tmp_path, "oos.txt", "admin.example.com\n")
    code = main(["match", "admin.example.com", "-s", scope, "-x", oos, "--json"])
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["results"][0]["disposition"] == "out-of-scope"


def test_missing_file_is_usage_error(tmp_path):
    assert main(["normalize", str(tmp_path / "nope.txt")]) == 2
