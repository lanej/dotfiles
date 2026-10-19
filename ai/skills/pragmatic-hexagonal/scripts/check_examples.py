"""Run reference detectors and isolated, intentionally broken copies.

A red experiment must fail its named expectation, not merely crash.
No network, production writes, provider SDK, or third-party packages required.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from decisions import Quote, select_quote
from operations import DemoProvider, LossyAdapter, Observation, attempt, reconcile


class ReferenceBehavior(unittest.TestCase):
    def test_expiry_boundary(self):
        # Independently specified acceptance example: at t=100 the one-cent
        # quote expired; among the usable quotes, beta costs less than gamma.
        quotes = [Quote("expired", 1, 100, True), Quote("beta", 120, 101, True),
                  Quote("gamma", 150, 110, True), Quote("ineligible", 2, 110, False)]
        self.assertEqual(select_quote(quotes, now=100), quotes[1],
                         "the expired quote must not win at its expiry instant")

    def test_timeout_and_reconciliation(self):
        provider = DemoProvider()
        result = attempt(provider, "order-7")
        self.assertEqual(result.state, "unknown", "timeout must preserve uncertainty")
        self.assertEqual(result.request_id, "order-7")
        self.assertIn("deadline", result.evidence)
        self.assertEqual(provider.attempts, 1, "uncertainty must not trigger a blind retry")
        resolved = reconcile(provider, result)
        self.assertEqual((resolved.state, resolved.evidence), ("confirmed", "receipt-42"))
        # A second possible world produces the same timeout, without an effect.
        # Neither failure nor success can be inferred from that observation.
        absent_provider = DemoProvider(commit=False)
        absent = attempt(absent_provider, "order-8")
        self.assertEqual(absent.state, "unknown")
        self.assertEqual(reconcile(absent_provider, absent), absent)

    def test_small_utility(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("utility.py"))],
                                input=b"pear\napple\npear\n\n apple\n", capture_output=True,
                                check=True, timeout=5)
        self.assertEqual(result.stdout, b"pear\napple\n\n apple\n")
        self.assertEqual(result.stderr, b"")

    def test_lossy_adapter(self):
        # Independent acceptance expectation: an incomplete market observation
        # must retain which provider rejected and which could not be observed.
        rejected = Observation("alpha", "rejected", "destination unsupported")
        unknown = Observation("beta", "unknown", "response deadline exceeded")
        result = LossyAdapter().summarize((rejected, unknown))
        self.assertEqual(result.evidence, (rejected, unknown),
                         "adapter must retain contradictory evidence")
        self.assertFalse(result.complete, "missing observations cannot establish market absence")


def detector(name: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(Path(__file__).resolve()), "--detector", name],
                          capture_output=True, text=True, timeout=10,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detector", choices=["expiry_boundary", "timeout_and_reconciliation",
                                              "small_utility", "lossy_adapter"])
    args = parser.parse_args()
    if args.detector:
        suite = unittest.TestSuite([ReferenceBehavior("test_" + args.detector)])
        return 0 if unittest.TextTestRunner().run(suite).wasSuccessful() else 1

    suite = unittest.TestSuite([ReferenceBehavior("test_expiry_boundary"),
                               ReferenceBehavior("test_timeout_and_reconciliation"),
                               ReferenceBehavior("test_small_utility")])
    if not unittest.TextTestRunner().run(suite).wasSuccessful():
        return 1
    # These are deliberate teaching experiments, not a compliance score.
    with tempfile.TemporaryDirectory(prefix="pha-defects-") as temporary:
        copied = Path(temporary) / "scripts"
        shutil.copytree(Path(__file__).parent, copied, ignore=shutil.ignore_patterns("__pycache__"))
        decision = copied / "decisions.py"
        original = decision.read_text()
        decision.write_text(original.replace("now < q.expires_at", "now <= q.expires_at", 1))
        broken = subprocess.run([sys.executable, str(copied / "check_examples.py"), "--detector",
                                 "expiry_boundary"], capture_output=True, text=True, timeout=10,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if broken.returncode != 1 or "the expired quote must not win" not in broken.stderr:
            raise RuntimeError("expiry defect did not fail the intended expectation: " + broken.stderr)
        print("RED as intended: expiry boundary admits expired quote")
        decision.write_text(original)
        restored = subprocess.run([sys.executable, str(copied / "check_examples.py"), "--detector",
                                   "expiry_boundary"], capture_output=True, text=True, timeout=10,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if restored.returncode:
            raise RuntimeError(restored.stderr)
        print("GREEN restored: expiry boundary")

        operation = copied / "operations.py"
        original = operation.read_text()
        operation.write_text(original.replace('Outcome(request_id, "unknown", str(error))',
                                               'Outcome(request_id, "failed", str(error))', 1))
        broken = subprocess.run([sys.executable, str(copied / "check_examples.py"), "--detector",
                                 "timeout_and_reconciliation"], capture_output=True, text=True, timeout=10,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if broken.returncode != 1 or "timeout must preserve uncertainty" not in broken.stderr:
            raise RuntimeError("timeout defect did not fail the intended expectation: " + broken.stderr)
        print("RED as intended: timeout loses uncertainty")
        operation.write_text(original)
        restored = subprocess.run([sys.executable, str(copied / "check_examples.py"), "--detector",
                                   "timeout_and_reconciliation"], capture_output=True, text=True, timeout=10,
                                  env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if restored.returncode:
            raise RuntimeError(restored.stderr)
        print("GREEN restored: timeout uncertainty")

    lossy = detector("lossy_adapter")
    if lossy.returncode != 1 or "adapter must retain contradictory evidence" not in lossy.stderr:
        raise RuntimeError("lossy adapter did not expose the evidence loss: " + lossy.stderr)
    print("RED as intended: tidy adapter destroys contradictory evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
