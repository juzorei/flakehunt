"""flakehunt: confirm and narrow flaky test failures instead of rerunning blindly."""

from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field

FAILED_SUMMARY = re.compile(r"^FAILED\s+(\S+)", re.M)
OUTCOME_LINE = re.compile(r"([0-9]+) (?:failed|passed)")


@dataclass
class Attempt:
    index: int
    exit_code: int
    seconds: float
    output_tail: str = ""
    failed_tests: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@dataclass
class Probe:
    command: str
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def verdict(self) -> str:
        if not self.attempts:
            return "error"
        oks = [a.ok for a in self.attempts]
        if all(oks):
            return "stable"
        if not any(oks):
            return "broken"
        return "flaky"

    @property
    def failed_count(self) -> int:
        return sum(1 for a in self.attempts if not a.ok)

    def failed_tests(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for a in self.attempts:
            for test in a.failed_tests:
                counts[test] = counts.get(test, 0) + 1
        return counts


def run_once(command: list[str], cwd: str | None = None, timeout: float = 300) -> Attempt:
    start = time.monotonic()
    proc = subprocess.run(command, capture_output=True, text=True, cwd=cwd, timeout=timeout,
                          shell=False)
    seconds = time.monotonic() - start
    combined = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(combined.strip().splitlines()[-12:])
    failed = sorted(set(FAILED_SUMMARY.findall(combined)))
    return Attempt(0, proc.returncode, round(seconds, 2), tail, failed)


def hammer(command: list[str], times: int = 20, cwd: str | None = None,
           stop_after: int | None = None) -> Probe:
    """Run the same command repeatedly; stop early once flakiness is proven."""
    stop_after = stop_after or max(2, times // 4 if times >= 8 else times)
    probe = Probe(" ".join(command))
    fails = 0
    for i in range(1, times + 1):
        attempt = run_once(command, cwd=cwd)
        attempt.index = i
        probe.attempts.append(attempt)
        if not attempt.ok:
            fails += 1
            if fails >= stop_after and i >= 3 and probe.verdict == "flaky":
                break  # pattern is established: some pass, some fail
    return probe


def seeds(base: list[str], seed_flag: str, first: int, last: int,
          cwd: str | None = None) -> Probe:
    """Run with each seed value; identify exactly which seeds reproduce the failure."""
    probe = Probe(" ".join(base) + f" [{first}..{last}]")
    for seed in range(first, last + 1):
        attempt = run_once([*base, f"{seed_flag}{seed}"], cwd=cwd)
        attempt.index = seed
        attempt.output_tail = f"seed {seed}\n" + attempt.output_tail
        probe.attempts.append(attempt)
    return probe


def describe(probe: Probe) -> str:
    if probe.verdict == "flaky":
        ok_runs = sum(1 for a in probe.attempts if a.ok)
        return (
            f"FLAKY confirmed: {ok_runs}/{len(probe.attempts)} passed, "
            f"{len(probe.attempts) - ok_runs} failed. It's real. Bisect order/seed with the "
            "failing runs below, or attach the failing seed to the ticket."
        )
    if probe.verdict == "broken":
        return ("BROKEN: every run failed — this is a deterministic failure, not a flake. "
                "Fix it like any failing test; reruns prove nothing.")
    if probe.verdict == "stable" and len(probe.attempts) < 3:
        return "INSUFFICIENT: fewer than 3 runs, no pattern yet."
    if probe.verdict == "stable":
        return (f"STABLE: all {len(probe.attempts)} runs passed. The flake didn't reproduce "
                "under these conditions — widen the probe (more runs, the full suite, "
                "parallelism) before concluding it's gone.")
    return "ERROR: no attempts recorded"
