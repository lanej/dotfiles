#!/usr/bin/env python3
"""Measure the current home's interactive login-shell startup and exit."""
import argparse
import json
import platform
import shutil
import statistics
import subprocess
import time


def positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=positive_int, default=30)
    parser.add_argument("--warmups", type=positive_int, default=3)
    parser.add_argument("--shell", default=shutil.which("zsh"))
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")
    args = parser.parse_args()
    if not args.shell:
        parser.error("zsh is not installed")
    command = [args.shell, "-d", "-i", "-l", "-c", "exit"]
    version = subprocess.check_output([args.shell, "--version"], text=True).strip()
    samples = []
    output_runs = 0
    for index in range(args.warmups + args.runs):
        started = time.perf_counter()
        result = subprocess.run(command, capture_output=True, timeout=15)
        elapsed_ms = (time.perf_counter() - started) * 1000
        if result.returncode:
            raise SystemExit(f"zsh exited with status {result.returncode}; investigate startup before benchmarking")
        if index >= args.warmups:
            samples.append(elapsed_ms)
            output_runs += bool(result.stdout or result.stderr)
    report = {
        "shell": version,
        "platform": f"{platform.system()} {platform.machine()}",
        "command": command,
        "runs": args.runs,
        "warmups": args.warmups,
        "median_ms": statistics.median(samples),
        "p95_ms": statistics.quantiles(samples, n=100, method="inclusive")[94] if len(samples) > 1 else samples[0],
        "min_ms": min(samples),
        "max_ms": max(samples),
        "runs_with_output": output_runs,
    }
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{version}; {report['platform']}")
        print("Interactive login shell startup + exit; global rc files skipped; inherited HOME/PATH.")
        print(f"{args.runs} runs after {args.warmups} warmups: "
              f"median {report['median_ms']:.1f} ms; p95 {report['p95_ms']:.1f} ms.")
        print(f"Shell output observed in {output_runs}/{args.runs} measured runs.")


if __name__ == "__main__":
    main()
