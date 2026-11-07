"""Quote selection over supplied facts; times and prices are integer units.

Contract: an eligible quote is usable only while now < expires_at.
Choose minimum (price_cents, quote_id); return None if none is usable.
Provider eligibility is supplied evidence, not verified by this function.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quote:
    quote_id: str
    price_cents: int
    expires_at: int
    eligible: bool


def select_quote(quotes: list[Quote], now: int) -> Quote | None:
    usable = [q for q in quotes if q.eligible and now < q.expires_at]
    return min(usable, key=lambda q: (q.price_cents, q.quote_id), default=None)
