# flakehunt

Prove and narrow flaky test failures instead of rerunning blindly.

A flake is only worth fixing once you can make it fail on demand. `flakehunt` runs the suspect command in a loop (or across seed values), classifies the outcome honestly, and tells you the next probe to run.

```text
$ flakehunt hammer "pytest -q tests/test_flaky.py" -n 20
command  pytest -q tests/test_flaky.py
runs     1:0 2:1 3:0 4:1 5:0 6:1
pattern  P F P F P F
verdict  FLAKY
advice   FLAKY confirmed: 3/6 passed, 3 failed. It's real. Bisect order/seed with the failing runs below...

$ flakehunt seeds "pytest tests/ -q" --from 1 --to 30
```

Three verdicts, three exit codes, no wishy-washy "seems flaky":

| Verdict | Exit | Meaning |
|---|---:|---|
| `FLAKY` | 3 | Some runs passed, some failed — a real flake. Narrow it. |
| `BROKEN` | 1 | Every run failed — a deterministic failure, not a flake. Reruns prove nothing. |
| `STABLE` | 0 | Didn't reproduce under these conditions; widen the probe before concluding. |

`hammer` runs one command N times with early stop once a pass/fail pattern is established; it prints which runs failed, which tests fail how often, the first failing output, and per-run timings. `seeds` runs the command with each seed value (`--flag` defaults to pytest-randomly's `--randomly-seed=`, override it for any other seeded runner) and reports exactly which seeds reproduce the failure.

`--json` everywhere for scripts and CI. Python 3.11+, stdlib only.

## Commands

```text
flakehunt hammer "<command>" [-n 20] [--stop-after N] [--json]
flakehunt seeds "<command>" [--flag --randomly-seed=] [--from 1] [--to 20] [--json]
```

Install: `pip install flakehunt` — or from this repo:

```bash
pip install "git+https://github.com/juzorei/flakehunt#subdirectory=tools/flakehunt"
```

The companion agent skill lives in [skills/flaky-test-hunting](../skills/flaky-test-hunting): confirm → narrow → fix → re-prove, with honest quarantine rules. Installing the skill: `npx skills add juzorei/flakehunt`.
