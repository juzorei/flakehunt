# flakehunt

[English](README.md) | [Русский](README.ru.md)

[![CI](https://github.com/juzorei/flakehunt/actions/workflows/ci.yml/badge.svg)](https://github.com/juzorei/flakehunt/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/github/license/juzorei/flakehunt)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/flakehunt)](https://pypi.org/project/flakehunt/)

An agent skill and a CLI that force honesty into flaky-test work: prove the flake before fixing it, then prove the fix.

The most common lie in test engineering is "fixed the flake" without a rerun loop that used to fail. The second most common is calling a deterministic failure a flake and rerunning until it "passes". `flakehunt` makes both impossible to say by accident:

```text
$ flakehunt hammer "pytest -q tests/test_flaky.py" -n 20
command  pytest -q tests/test_flaky.py
runs     1:0 2:1 3:0 4:1 5:0 6:1
pattern  P F P F P F
verdict  FLAKY
advice   FLAKY confirmed: 3/6 passed, 3 failed. It's real. Bisect order/seed with the failing runs below...
```

## What's in the repo

- **[skills/flaky-test-hunting](skills/flaky-test-hunting)** — the workflow for coding agents: confirm the flake (hammer), narrow it (seed hunt for order dependence, repeats for resource accumulation, parallelism for isolation bugs), fix the narrowest demonstrated cause, then re-run the exact probe that used to fail. Both `STABLE` or it isn't fixed. Honest quarantine: linked issue + expiry date, never a silent skip.
- **tools/flakehunt** — the CLI ([README](tools/flakehunt/README.md)): `hammer` (rerun loop with early stop and a pass/fail pattern line), `seeds` (which seed values reproduce the failure), three verdicts with distinct exit codes (`FLAKY`/`BROKEN`/`STABLE`), `--json` for CI, stdlib only.

## Install

```bash
pip install flakehunt
npx skills add juzorei/flakehunt
```

## More from this portfolio

Part of a series of focused skill+CLI tools by the same author:

- [ci-autopsy](https://github.com/juzorei/ci-autopsy) — classify failed runs before rerunning them
- [loglens](https://github.com/juzorei/loglens) — when the flake left its trace in the logs
- [bumpmap](https://github.com/juzorei/bumpmap) — did the upgrade break it or is it a flake?

Browse the rest at the [juzorei profile](https://github.com/juzorei?tab=repositories).

## Scope

Run the probes against suites you own; hammering external services pushes your CI load onto someone else's quota — such tests belong behind mocks.

MIT licensed.
