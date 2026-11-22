---
name: rust
description: "Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Use when writing, testing, or debugging Rust code and optimizing build efficiency. Prefer cargo check over build and avoid release builds unless explicitly needed. Don't use for C/C++, Go, or other compiled languages. Apply the selected beta expectations."
---

# rust: beta

Run check-only formatting, meaningful tests, and Clippy before delivery. Use `cargo check` for iterative compile feedback. Broaden happy paths, important failures, and relevant integration and compatibility checks.

<!-- source-code:shared-guidance -->
