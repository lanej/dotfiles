---
name: rust
description: "Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Use when writing, testing, or debugging Rust code and optimizing build efficiency. Prefer cargo check over build and avoid release builds unless explicitly needed. Don't use for C/C++, Go, or other compiled languages. Apply the selected research expectations."
---

# rust: research

Begin with `cargo check` for compile feedback and exercise the real experiment. Keep the useful steel-thread regression check; do not automatically add a broad test or Clippy pass unless repository requirements or consequences call for it.

<!-- source-code:shared-guidance -->
