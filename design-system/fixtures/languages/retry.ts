// Keep transport separate from retry policy.
type Result<T> = { ok: true; value: T }
  | { ok: false; reason: string };

interface Policy {
  delay(attempt: number): Promise<number>;
}

async function decide<T>(p: Policy, n: number): Promise<Result<T>> {
  const ms = await p.delay(n);
  return { ok: false, reason: `retry in ${ms}ms` };
}
