# Router API contract

The router is a transparent regional proxy for Bedrock Mantle's OpenAI-compatible
HTTP API. It owns regional routing and transport behavior, while Bedrock owns
request validation and response schemas.

## Upstream reference

The upstream reference is OpenAI's OpenAPI 3.1 specification, pinned in
[`upstream-contract.json`](upstream-contract.json). It includes Responses,
compaction, token counting, Models, and streaming event schemas. AWS documents
Mantle compatibility in its [Responses API guide](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-responses-api.html).
This reference is not a promise that Mantle implements every OpenAI operation.

The schema is a reference for compatibility reviews, not a runtime validator or
generated server interface. Updating the pin requires reviewing changes to
operations and fields inspected by the router against AWS's supported behavior.
Unknown JSON fields and stream events must continue to pass through.

## Proxy boundary

- Accept relative HTTP paths under `/openai/v1/` with bearer authorization.
  Forward the method, path, query, body bytes, and end-to-end headers unchanged.
  Hop-by-hop headers and the router's own request ID are excluded.
- Inspect only the top-level `model` for routing. Empty bodies are accepted;
  nonempty bodies must be JSON objects, optionally gzip encoded. The encoded
  and decoded body limits are each 128 MiB.
- After the specific streamed error `Access denied: web search is not authorized
  for this identity.`, append a developer recovery hint to the next response
  creation request in that session. The hint asks the model to avoid repeating
  the denied call unchanged and continue useful work. Tools, existing input
  items (including encrypted history), and unknown fields are preserved.
  This is the only request-body rewriting exception. The pending hint expires
  after 15 minutes and does not survive a router restart.
- The separate `browse-mcp` stdio command exposes `bedrock_browse`. It submits
  only the supplied research task to its configured model and region, without
  using the proxy's session pins or replaying the caller's generation. Tool
  results contain the browsing answer and citation URLs. No task or result is
  logged; upstream error bodies are not returned.
- Relay upstream statuses, response bytes, and SSE bytes without schema
  decoding or serialization. Streaming transport removes fixed content lengths
  so incomplete streams can be reported.
- Forward unrecognized operations within the proxy boundary to Bedrock, subject
  to routing requirements. The upstream decides whether they are supported.

## Region selection

Collection operations such as `/responses`, `/responses/compact`, and
`/responses/input_tokens` use the session's region, then its parent's region,
then the configured model region, then the default region.

Operations under `/responses/{response_id}`, including retrieval, deletion,
cancellation, and input-item listing, require an existing pin for the originating
session. They do not require a body `model`. Without that pin, return `409` with
`error.code = "region_unknown"` before contacting Bedrock. A model or parent pin
alone cannot establish which region owns a stored response. Response IDs are
opaque; the router does not store response-to-region mappings.

Session identity is taken from `Thread-Id`, then `thread_id` or `session_id` in
`X-Codex-Turn-Metadata`, then `Session-Id`. Parent identity is taken from
`X-Codex-Parent-Thread-Id`, then `parent_thread_id` or `forked_from_thread_id`
in the metadata. Only hashed identities and region pins are persisted.

A successful request with a nonempty model records its session region. Pins
remain fixed across restarts and model changes. A conflicting configured model
region returns `409` with `error.code = "region_conflict"`.

Only an unpinned request rejected explicitly for encrypted-context region
validation can attempt the configured alternate region, once, using the same
request bytes. Transport failures, generations, and partial streams are never
replayed.

## Local operations and failures

`GET /healthz` returns the router's JSON status; `GET /metrics` returns Prometheus
metrics. These local operations do not require bearer authorization.

Router errors use `{"error":{"code":"…","message":"…"}}`. Invalid paths return
`404`; missing bearer authorization returns `401`; invalid bodies return `400`;
state failures return `503`; upstream connection failures return `502`; upstream
timeouts before headers return `504`. Failures after headers abort the stream.
Requests receive `X-Router-Request-Id` for correlation with metadata-only logs.

The HTTP lifecycle detector in `router_test.go` exercises creation with an
unknown field, retrieval, cancellation, deletion, byte preservation, and
rejection when the session region is unknown. Existing routing and streaming
detectors cover region affinity, recovery, concurrency, and transport failures.
