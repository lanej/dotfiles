from dataclasses import dataclass

@dataclass(frozen=True, repr=False)
class Policy:
    delays: tuple[int, ...] = (100, 200, 400)

    def remaining(self, attempt: int) -> list[int]:
        return [ms for i, ms in enumerate(self.delays)
                if i >= attempt]

    def next_delay(self, attempt: int) -> int | None:
        return next(iter(self.remaining(attempt)), None)

def describe(policy: Policy) -> str:
    return f"retry budget: {len(policy.delays)}"
