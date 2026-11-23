---
name: rust
description: "Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Use when writing, testing, or debugging Rust code and optimizing build efficiency. Prefer cargo check over build and avoid release builds unless explicitly needed. Don't use for C/C++, Go, or other compiled languages. Apply the selected production expectations."
---

# rust: production

Run check-only formatting, meaningful tests, and Clippy, plus the relevant independent review and recovery or operational checks. Protect consequential supported behavior without duplicating implementation details in tests.

<!-- source-code:shared-guidance -->
