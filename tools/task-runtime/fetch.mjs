// Both packages run requests in Node. The Paseo mobile declarations also define a different global AbortSignal.
export function fetchBeads(request) {
  return globalThis.fetch(request, {
    signal: AbortSignal.timeout(30_000),
    redirect: "error",
  });
}
