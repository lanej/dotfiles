"""Simulated external operation: a lost response cannot establish the effect.

The provider is a teaching fake, not a production client or retry framework.
A real integration should use its official SDK and authoritative receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Outcome:
    request_id: str
    state: Literal["confirmed", "failed", "unknown"]
    evidence: str


class DemoProvider:
    """Model an effect whose response is lost, with or without a commit."""

    def __init__(self, commit: bool = True):
        self.commit = commit
        self.receipts: dict[str, str] = {}
        self.attempts = 0

    def create(self, request_id: str) -> str:
        self.attempts += 1
        if self.commit:
            self.receipts[request_id] = "receipt-42"
        raise TimeoutError("response deadline exceeded")

    def lookup(self, request_id: str) -> str | None:
        return self.receipts.get(request_id)


def attempt(provider: DemoProvider, request_id: str) -> Outcome:
    """Execute the intended create once; distinguish attempt from confirmation."""
    try:
        receipt = provider.create(request_id)
    except TimeoutError as error:
        return Outcome(request_id, "unknown", str(error))
    return Outcome(request_id, "confirmed", receipt)


def reconcile(provider: DemoProvider, previous: Outcome) -> Outcome:
    receipt = provider.lookup(previous.request_id)
    if receipt is not None:
        return Outcome(previous.request_id, "confirmed", receipt)
    # This lookup's absence is not authoritative proof of non-completion.
    return previous


@dataclass(frozen=True)
class Observation:
    provider: str
    state: Literal["eligible", "rejected", "unknown"]
    detail: str


@dataclass(frozen=True)
class AvailabilityReport:
    eligible_providers: tuple[str, ...]
    complete: bool
    evidence: tuple[Observation, ...]


def eligible_providers(names: tuple[str, ...]) -> tuple[str, ...]:
    """A pure core over the canonical model supplied by the adapter."""
    return names


class LossyAdapter:
    """Deliberately noncompliant despite a pure core and separate adapter.

    The canonical tuple erases rejection vs missing observations and provenance.
    The published report cannot reveal whether 'none' was observed or inferred.
    The report is all the caller retains; raw observations are not archived.
    """

    def summarize(self, observations: tuple[Observation, ...]) -> AvailabilityReport:
        normalized = tuple(obs.provider for obs in observations if obs.state == "eligible")
        selected = eligible_providers(normalized)
        return AvailabilityReport(selected, complete=True, evidence=())
