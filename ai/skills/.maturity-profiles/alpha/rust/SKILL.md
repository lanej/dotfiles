---
name: rust
description: "Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Use when writing, testing, or debugging Rust code and optimizing build efficiency. Prefer cargo check over build and avoid release builds unless explicitly needed. Don't use for C/C++, Go, or other compiled languages. Apply the selected alpha expectations."
---

# rust: alpha

Run check-only formatting and affected retained-behavior tests, using `cargo check` for compile feedback as needed. Prioritize primary happy paths and keep provisional interfaces easy to change. Preserve stronger existing project requirements.

<!-- source-code:shared-guidance -->
