"""Apply the pre-registered decision rule in DESIGN.md to collected runs.

The verdict is computed mechanically. Do not reinterpret an INCONCLUSIVE result
after the fact; inconclusive means keep the clause.
"""
import argparse
import json
import math
import pathlib
import sys

ARMS = ("omit", "state")
OUTCOMES = ("test_first", "impl_first", "no_test", "no_impl")
DELETE_BAR = 18  # test_first runs out of 20 the omit arm must clear
ALPHA = 0.05


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact p-value for [[a, b], [c, d]]."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    row1, col1 = a + b, a + c

    def prob(x):
        return (math.comb(row1, x) * math.comb(n - row1, col1 - x)) / math.comb(n, col1)

    observed = prob(a)
    low = max(0, col1 - (n - row1))
    high = min(row1, col1)
    return min(1.0, sum(prob(x) for x in range(low, high + 1)
                        if prob(x) <= observed + 1e-12))


def load(outdir):
    runs = {arm: [] for arm in ARMS}
    for arm in ARMS:
        for path in sorted((pathlib.Path(outdir) / arm).glob("t*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    runs[arm].append(json.loads(line))
    return runs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outdir")
    args = parser.parse_args(argv)

    runs = load(args.outdir)
    counts, scored = {}, {}
    for arm in ARMS:
        counts[arm] = {o: sum(1 for r in runs[arm] if r["outcome"] == o) for o in OUTCOMES}
        # no_impl is degenerate: the task never happened, so it is not evidence
        # either way. DESIGN.md calls for re-drawing those runs.
        scored[arm] = len(runs[arm]) - counts[arm]["no_impl"]

    print(f"{'arm':<6} {'n':>4} {'test_first':>11} {'impl_first':>11} {'no_test':>8} {'no_impl':>8}   rate")
    for arm in ARMS:
        c = counts[arm]
        rate = c["test_first"] / scored[arm] if scored[arm] else float("nan")
        print(f"{arm:<6} {scored[arm]:>4} {c['test_first']:>11} {c['impl_first']:>11} "
              f"{c['no_test']:>8} {c['no_impl']:>8}   {rate:.0%}")

    a, b = counts["omit"]["test_first"], scored["omit"] - counts["omit"]["test_first"]
    c, d = counts["state"]["test_first"], scored["state"] - counts["state"]["test_first"]
    p = fisher_exact(a, b, c, d)
    print(f"\nFisher exact (two-sided): p = {p:.4f}")

    incomplete = [arm for arm in ARMS if scored[arm] < 20]
    if incomplete:
        print(f"\nINCOMPLETE — {', '.join(incomplete)} has fewer than 20 scored runs. "
              "Re-draw degenerate runs before reading a verdict.")
        return 1

    p_omit = a / scored["omit"]
    p_state = c / scored["state"]
    if a >= DELETE_BAR and p > ALPHA:
        verdict = ("DELETE — the omit arm cleared the absolute bar and the arms are "
                   "not distinguishable. This bounds the failure rate near 15%, it "
                   "does not establish safety.")
    elif p <= ALPHA and p_state > p_omit:
        verdict = "KEEP — the clause changes behavior."
    else:
        verdict = "INCONCLUSIVE — keep the clause. More trials, not reinterpretation."
    print(f"\nomit {p_omit:.0%} vs state {p_state:.0%}\nVERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
