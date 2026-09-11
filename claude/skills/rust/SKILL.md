---
name: rust
description: Rust development with cargo - build strategy, clippy triage, testing workflows, and lint configuration. Prefer cargo check over cargo build; avoid release builds unless explicitly needed.
---

# Rust / cargo

Standard cargo usage works as documented. This file covers build-cost discipline and clippy triage,
where the default instinct is usually wrong.

## Build strategy: never reach for `--release`

Release builds and `cargo install --path .` are very slow and almost never what iteration needs.

| Goal | Command |
|---|---|
| Does it compile? | `cargo check` — fastest, no codegen |
| Developing / testing behavior | `cargo run` (or `cargo run -- args`) |
| Need the binary artifact only | `cargo build` (debug) |
| Need optimized performance | `cargo build --release` — only then |

## Validation order

```bash
cargo test --quiet
cargo check --quiet
cargo clippy
```

Tests first (logic errors surface earliest), then check, then clippy. Use `cargo check`, not
`cargo build`, for validation.

**Timeouts**: 120s covers check/test/debug builds. Only a release build needs 600s — if you're
reaching for the long timeout, question whether the release build is needed at all.

## Clippy triage

Auto-fix first, then categorize what remains — do not blanket-fix or blanket-allow:

```bash
cargo clippy --fix --allow-dirty
cargo clippy --explain <LINT_NAME>   # when the lint's intent is unclear
```

**Fix**: `redundant_closure`, `unnecessary_unwrap`, `manual_map`, `match_same_arms`,
`needless_return`, and anything indicating a real panic, logic error, or API misuse.

**Suppress** when the domain guarantees safety: `cast_possible_truncation`, `cast_sign_loss`,
`missing_errors_doc` / `missing_panics_doc` (internal tools), `needless_pass_by_value`,
`module_name_repetitions`, `too_many_lines`, `unused_assignments` (loop invariants).

Suppress at the narrowest scope that works — function `#[allow(...)]`, then module `#![allow(...)]`,
then `[lints.clippy]` in `Cargo.toml`. Always leave a comment stating the domain invariant:

```rust
#[allow(clippy::cast_possible_truncation)]
fn process_excel_value(val: u64) -> u32 {
    val as u32  // Excel row numbers are always < u32::MAX
}
```

The goal is a clippy run where every remaining warning is actionable.

## Cargo lock contention

"resource busy", Cargo.lock contention, or a hanging build usually means orphaned cargo processes:

```bash
pkill -f cargo
```

## Cargo.toml style

Comments go on their own line, never inline after a dependency entry.
