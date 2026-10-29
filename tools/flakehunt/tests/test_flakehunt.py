import json
import sys
import textwrap

import pytest

from flakehunt.cli import VERDICT_EXIT, main, probe_json, print_report
from flakehunt.runner import Attempt, Probe, describe, hammer, seeds

PY = sys.executable


def flaky_script(tmp_path, period, seedable=False):
    """A python script that fails when a counter file hits `period` (i.e., every Nth run)."""
    script = tmp_path / "flaky.py"
    if seedable:
        script.write_text(textwrap.dedent(f"""
            import sys
            seed = int(next(a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--s=")))
            sys.exit(1 if seed % {period} == 0 else 0)
        """), encoding="utf-8")
    else:
        script.write_text(textwrap.dedent(f"""
            from pathlib import Path
            c = Path(__file__ + ".count")
            n = int(c.read_text() or 0) + 1 if c.exists() else 1
            c.write_text(str(n))
            sys_exit = 1 if n % {period} == 0 else 0
            raise SystemExit(sys_exit)
        """), encoding="utf-8")
    return str(script)


def flaky_pytest_project(tmp_path):
    (tmp_path / "test_flaky.py").write_text(textwrap.dedent("""
        from pathlib import Path
        def test_sometimes():
            c = Path(__file__ + ".count")
            n = int(c.read_text() or 0) + 1 if c.exists() else 1
            c.write_text(str(n))
            assert n % 3 != 0
    """), encoding="utf-8")
    return tmp_path


def test_hammer_detects_flake(tmp_path):
    script = flaky_script(tmp_path, period=2)
    probe = hammer([PY, script], times=6, stop_after=3)
    assert probe.verdict == "flaky"
    assert 1 <= probe.failed_count <= 5


def test_hammer_broken_is_not_flaky(tmp_path):
    broken = tmp_path / "broken.py"
    broken.write_text("raise SystemExit(1)\n", encoding="utf-8")
    probe = hammer([PY, str(broken)], times=3, stop_after=1)
    assert probe.verdict == "broken"


def test_hammer_stable_and_startles_noone(tmp_path):
    ok = tmp_path / "ok.py"
    ok.write_text("print('fine')\n", encoding="utf-8")
    probe = hammer([PY, str(ok)], times=3)
    assert probe.verdict == "stable" and all(a.ok for a in probe.attempts)


def test_seeds_finds_bad_seeds(tmp_path):
    script = flaky_script(tmp_path, period=4, seedable=True)
    probe = seeds([PY, script], "--s=", 1, 8)
    assert probe.attempts[3].exit_code == 1
    assert [a.index for a in probe.attempts if not a.ok] == [4, 8]


def test_describe_words(tmp_path):
    ok = tmp_path / "ok.py"
    ok.write_text("pass\n", encoding="utf-8")
    probe = hammer([PY, str(ok)], times=2)
    assert "INSUFFICIENT" in describe(probe)
    probe2 = hammer([PY, str(ok)], times=3)
    assert "didn't reproduce" in describe(probe2)
    assert "deterministic" in describe(Probe("x", [Attempt(1, 1, 0), Attempt(2, 1, 0)]))


def test_probe_records_tail_on_failure(tmp_path):
    failing = tmp_path / "failing.py"
    failing.write_text("import sys; print('boom trace'); sys.exit('1')\n", encoding="utf-8")
    probe = hammer([PY, str(failing)], times=1)
    assert "boom trace" in probe.attempts[0].output_tail


def test_cli_hammer_exit_codes(tmp_path, capsys):
    script = flaky_script(tmp_path, period=2)
    rc = main(["hammer", f'"{PY}" "{script}"', "-n", "4", "--stop-after", "1", "--json"])
    assert rc == VERDICT_EXIT["flaky"] == 3
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "flaky" and 0 < out["failed"] < out["runs"]


def test_cli_broken_exit_one(tmp_path, capsys):
    broken = tmp_path / "b.py"
    broken.write_text("raise SystemExit(3)\n", encoding="utf-8")
    assert main(["hammer", f'"{PY}" "{broken}"', "-n", "2", "--json"]) == 1


def test_cli_seeds(tmp_path, capsys):
    script = flaky_script(tmp_path, period=3, seedable=True)
    rc = main(["seeds", f'"{PY}" "{script}"', "--flag=--s=", "--from", "1", "--to", "3", "--json"])
    assert rc == 3  # flaky: seed 3 fails, 1-2 pass
    out = json.loads(capsys.readouterr().out)
    assert out["failing_runs"] == [3] and out["verdict"] == "flaky"


def test_cli_text_report_has_pattern(tmp_path, capsys):
    script = flaky_script(tmp_path, period=2)
    main(["hammer", f'"{PY}" "{script}"', "-n", "4", "--stop-after", "1"])
    out = capsys.readouterr().out
    assert "pattern" in out and "FLAKY" in out and "P" in out and "F" in out


def test_cli_bad_command():
    assert main(["hammer", ""]) == 2


def test_cli_missing_binary():
    assert main(["hammer", "definitely-not-a-real-binary-xyz -v"]) == 2
