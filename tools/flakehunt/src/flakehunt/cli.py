"""flakehunt CLI: prove a flake before fixing it, then narrow it."""

from __future__ import annotations

import argparse
import json
import shlex
import sys

from . import __version__
from .runner import Probe, describe, hammer, seeds

VERDICT_EXIT = {"flaky": 3, "broken": 1, "stable": 0, "error": 2, "insufficient": 4}


def probe_json(probe: Probe) -> dict:
    return {
        "command": probe.command,
        "verdict": probe.verdict,
        "runs": len(probe.attempts),
        "passed": sum(1 for a in probe.attempts if a.ok),
        "failed": sum(1 for a in probe.attempts if not a.ok),
        "seconds_total": round(sum(a.seconds for a in probe.attempts), 2),
        "failing_runs": [a.index for a in probe.attempts if not a.ok],
        "failed_tests": probe.failed_tests(),
        "attempts": [{"run": a.index, "exit": a.exit_code, "seconds": a.seconds}
                     for a in probe.attempts],
    }


def print_report(probe: Probe) -> None:
    line = " ".join("P" if a.ok else "F" for a in probe.attempts)
    print(f"command  {probe.command}")
    print(f"runs     {' '.join(f'{a.index}:{a.exit_code}' for a in probe.attempts)}")
    print(f"pattern  {line}")
    counts = probe.failed_tests()
    if counts:
        worst = sorted(counts.items(), key=lambda kv: -kv[1])
        for test, count in worst[:5]:
            print(f"failed   {test} ({count}/{len(probe.attempts)} runs)")
    print(f"verdict  {probe.verdict.upper()}")
    print(f"advice   {describe(probe)}")
    for attempt in probe.attempts:
        if not attempt.ok:
            print(f"--- first failing run output (run {attempt.index}) ---")
            print(attempt.output_tail or "(no output captured)")
            break


def parse_command(text: str) -> list[str]:
    parts = shlex.split(text)
    if not parts:
        raise ValueError("empty command")
    return parts


def cmd_hammer(args) -> int:
    probe = hammer(parse_command(args.command), times=args.times, stop_after=args.stop_after)
    if args.json:
        print(json.dumps(probe_json(probe), indent=2))
    else:
        print_report(probe)
    return VERDICT_EXIT[probe.verdict]


def cmd_seeds(args) -> int:
    base = parse_command(args.command)
    probe = seeds(base, args.flag, args.from_seed, args.to_seed)
    if args.json:
        print(json.dumps(probe_json(probe), indent=2))
    else:
        print_report(probe)
    return VERDICT_EXIT[probe.verdict]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flakehunt", description=__doc__)
    parser.add_argument("--version", action="version", version=f"flakehunt {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("hammer", help="run one command N times and classify the outcome")
    p.add_argument("command", help="quoted command, e.g. \"pytest -q tests/test_flaky.py\"")
    p.add_argument("-n", "--times", type=int, default=20)
    p.add_argument("--stop-after", type=int, default=None,
                   help="stop this many failures early once flakiness is proven (default: ~1/4 of runs)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_hammer)

    p = sub.add_parser("seeds", help="run with each seed value (pytest-randomly, PYTHONHASHSEED, ...)")
    p.add_argument("command")
    p.add_argument("--flag", default="--randomly-seed=",
                   help="seed flag glued to the value (default --randomly-seed=; "
                        "use --env PYTHONHASHSEED= via your shell, or e.g. -k)")
    p.add_argument("--from", dest="from_seed", type=int, default=1)
    p.add_argument("--to", dest="to_seed", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_seeds)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ValueError as exc:
        print(f"flakehunt: error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"flakehunt: error: command not found: {exc.filename}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nflakehunt: interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
