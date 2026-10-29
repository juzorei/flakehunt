---
name: flaky-test-hunting
description: Confirm and pin down a flaky test before fixing it — rerun hammers, seed hunts, order bisection, isolation analysis. Use whenever a test "sometimes fails", CI is green-then-red on the same commit, a nightly fails but the same tests pass on a PR, the user says "flaky", "intermittent failure", "works on my machine fails in CI", "rerun and it passed", asks to "confirm this flake", or proposes to fix a test that was seen failing only once. Covers pytest-randomly seeds, pytest-repeat hammering, order bisecting, resource/timing causes, and honest quarantine.
---

# Flaky test hunting

A flake is only worth fixing once you can *make it fail on demand*. Until then, any "fix" is a coin flip that you cannot verify. This skill's contract: **confirm, narrow, then fix — and never claim a flake is fixed without a rerun loop that used to fail and now passes.**

Install the CLI:

```bash
pip install flakehunt
```

## 1. Confirm the flake (minutes, not hours)

Run the suspect command repeatedly and let the pattern speak:

```bash
flakehunt hammer "pytest -q tests/test_flaky.py" -n 20
```

Output (exit code 3 means flake proven):

```text
command  pytest -q tests/test_flaky.py
runs     1:0 2:1 3:0 4:1 5:0 6:1
pattern  P F P F P F
verdict  FLAKY
advice   FLAKY confirmed: 3/6 passed, 3 failed...
--- first failing run output (run 2) ---
...
```

The three verdicts and what they mean:

- `FLAKY` (exit 3) — some passed, some failed. Real flake: go to step 2.
- `BROKEN` (exit 1) — every run failed. **This is not a flake.** It's a deterministic failure (possibly order-dependent on the suite); fix it as a normal failing test with the full-suite reproduction.
- `STABLE` (exit 0) — all runs passed under these conditions. The flake needs more pressure: run the *whole suite* around it, add parallelism (`-p xdist -n 4`), or a longer loop. A flake you cannot reproduce cannot be verified as fixed either — say so.

`--json` gives machine-readable results (failing run numbers, per-attempt timings); failing tests are counted across runs so you see `test_x (7/20 runs)`.

## 2. Narrow: which axis does it flake on?

Pick the probe that matches how the failure was reported:

- **Fails in the full suite, passes alone → order dependence.** Hunt the seed:

  ```bash
  pytest tests/ -q                       # note: pytest-randomly shuffles by default
  flakehunt seeds "pytest tests/ -q" --from 1 --to 30   # each --randomly-seed value, reported per seed
  ```

  Once one seed reproduces it: `pytest tests/ -q --randomly-seed=<bad>` is your on-demand failure. Bisect by halving the test list until two tests alone reproduce it — the first of the pair leaks state into the second. Usual leakers: module-level mocks, DB rows without teardown, `cwd`/`sys.path` mutation, open transaction pools.

- **Fails standalone over many repeats → resource accumulation.** A counter file, an appending list, a port held by a previous instance of itself:

  ```bash
  flakehunt hammer "pytest tests/test_flaky.py -q" -n 20
  ```

  paired with `--count=20` (pytest-repeat) for in-process repeats.

- **Fails on loaded/slow runners, passes locally → timing.** Look for sleeps ("wait 2s for the server"), wall-clock assertions, and readiness checks without polling. Never "fix" by raising the sleep: poll with a deadline instead.

- **Fails under parallelism only → true isolation bug.** Shared port (fix: bind port 0), shared file path (fix: `tmp_path`, which xdist already makes unique per worker), a shared DB without per-worker schema.

## 3. Fix, then prove the fix

Fix the narrowest cause you demonstrated in step 2 — reset the leaked state in a fixture, poll instead of sleep, bind ephemeral ports. Then **rerun the exact probe that used to fail**:

```bash
flakehunt hammer "pytest -q tests/test_flaky.py" -n 20      # was FLAKY
flakehunt seeds "pytest tests/ -q" --from 1 --to 30         # all seeds green now
```

Both `STABLE` or it isn't fixed. Writing "fixed the flake" without this rerun is the most common lie in flake work.

## 4. Quarantine honestly (only if you must ship)

If the flake is confirmed but the fix needs time:

1. Mark it with the linked issue in the mark reason.
2. Set an expiry date — after it, quarantine lapses and the test blocks CI again.
3. Never silently skip. A growing quarantine count means the team should schedule a stability batch, not that the suite is healthy.

A quarantine that hides a *deterministically* broken test (step 1 said BROKEN, not FLAKY) is a lie with an expiration date — don't.

## 5. Report

```text
flake:    tests/test_server.py::test_rebind confirmed FLAKY (11/20 runs failed)
narrowed: order dependence — seed 174 reproduces (port fixture leaks between tests A and B)
fixed:    port=0 in the server fixture; seeds 1-30 now all green
```

If you couldn't reproduce it, report that honestly with the probes you ran — "not reproduced under 20 standalone runs and 30 seeds" is a result, not a failure.

## Scope

Run these probes against test suites the user owns or is authorized to work on. Hammering external services through their tests means your CI load falls on someone else's quota — flag tests that hit real third-party APIs and suggest mocks instead.
