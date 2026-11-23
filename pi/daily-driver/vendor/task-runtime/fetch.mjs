// Keep the runtime fetch boundary independent of consumer-specific global declarations.
export function fetchBeads(request) {
  return globalThis.fetch(request, {
    signal: AbortSignal.timeout(30_000),
    redirect: "error",
  });
}
