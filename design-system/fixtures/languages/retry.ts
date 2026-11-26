// Keep transport separate from retry policy.
type Result<T> = { ok: true; value: T }
  | { ok: false; reason: string | null };

interface Policy {
  delay(attempt: number): Promise<number>;
}

async function decide(p: Policy, n: number): Promise<Result<number>> {
  if (n < 0) return { ok: false, reason: null };
  const ms = await p.delay(n);
  if (ms > 0) return { ok: true, value: ms };
  return { ok: false, reason: `retry in ${ms}ms` };
}
