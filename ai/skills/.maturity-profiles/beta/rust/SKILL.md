---
name: rust
description: "Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Use when writing, testing, or debugging Rust code and optimizing build efficiency. Prefer cargo check over build and avoid release builds unless explicitly needed. Don't use for C/C++, Go, or other compiled languages. Apply the selected beta expectations."
---

# rust: beta

Run check-only formatting, meaningful tests, and Clippy before delivery. Use `cargo check` for iterative compile feedback. Broaden happy paths, important failures, and relevant integration and compatibility checks.

Read [shared guidance](references/common.md) for invariant rules and tool mechanics. Command examples there describe available capabilities; they do not add checks beyond this selected entrypoint and the repository's requirements. When selecting verification, use the installed testing guidance for minimum effective coverage and useful CLI diagnostics. Preserve authored project requirements and explicit authority limits.
