from dataclasses import dataclass

@dataclass(frozen=True)
class Policy:
    delays: tuple[int, ...] = (100, 200, 400)

    def remaining(self, attempt: int) -> list[int]:
        return [ms for i, ms in enumerate(self.delays)
                if i >= attempt]

def describe(policy: Policy) -> str:
    return f"retry budget: {len(policy.delays)}"
