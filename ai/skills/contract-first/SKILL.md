---
name: contract-first
description: Use when designing or changing API, provider, wire, schema, or generated-code boundaries. Establish authoritative contracts and generate mechanical code before implementing adapters or application policy.
---

# Contract first

Make authoritative contracts the source of truth and generate as much mechanical code as practical. Keep application meaning and policy explicitly owned. Follow the target project's installed engineering guidance, retained behavior and authorization limits.

## Establish the contract

Identify the owner and authoritative source before changing a boundary: a maintained schema, protocol specification, command definition or provider contract. Separate intended guarantees from observed samples and current implementation. Record consequential gaps; samples alone cannot establish a closed enum, required field or supported operation.

For external providers, evaluate suitable official SDKs, then maintained ecosystem clients before building a replacement. Reuse their protocol implementation and provider types when they meet the contract. Assess configuration, wrappers and narrow fixes before rejecting reuse; generating a duplicate client is not an end in itself.

When reuse is unsuitable, generate from sourced authoritative contracts. For application-owned interfaces, change the owning contract first and regenerate its consumers. Handwritten protocol code is the final fallback: identify why reuse and generation cannot satisfy the requirement, the retained validation and a condition for revisiting that choice. Missing specifications alone do not justify skipping client evaluation.

## Generate the mechanical parts

Derive types, clients, server bindings, serialization, validation, command/help definitions and reference material from their authoritative owners where supported. Prefer one contract with generated consumers over manually synchronized representations. Do not create a new schema layer for behavior already owned by a suitable SDK or existing project source.

For HTTP APIs, source the authoritative specification. JSON samples or a standalone JSON Schema do not supply the full HTTP contract; establish the missing operations and protocol semantics before generation. Follow the target language guidance for generator selection.

Use the project's pinned tools and generation commands. Never edit generated output by hand. Review changes to the authoritative input and the generated diff together; preserve compatibility and verify that regeneration reproduces the output. Generated validation must be invoked where the tool requires it; generated types alone do not prove runtime validation.

Keep credentials, destinations, resource bounds, cancellation, retry policy and application decisions outside mechanical translation unless the owning contract specifies them. Preserve absence, explicit zero/false, precision, timestamps, bytes, open values, error distinctions and consequential provenance. Unknown effects remain unknown; generation supplies no permission to retry, replay or execute.

## Verify the consuming boundary

Exercise one real entrypoint through the generated or reused boundary to an observable result. Check integration behavior against independently sourced expectations, including consequential failure and compatibility cases. Successful generation proves neither provider behavior nor installed or live acceptance.

Test application integration, local policy and patches rather than routinely rerunning unchanged upstream suites. Pin selected client and generator provenance; preserve licenses. Document consequential patches, their focused regression evidence and when they can be removed.

Update affected consumers and operational guidance in the same change. Keep project-specific contract locations, commands and evidence limits in the owning project; the shared workflow does not replace those requirements.
