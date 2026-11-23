// Resolve AbortSignal at runtime to avoid the conflicting Paseo mobile declarations.
export function fetchBeads(request) {
  return globalThis.fetch(request, {
    signal: AbortSignal.timeout(30_000),
    redirect: "error",
  });
}
