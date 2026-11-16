# shortpath

A small, dependency-free Rust CLI for compact path labels. Each component keeps just enough characters to distinguish it from its filesystem siblings. The final component stays full by default.

```text
projects/payments/src/main.rs  →  proj/paym/s/main.rs
```

Use it for shell prompts, terminal titles, logs, and picker labels. **Output is for display:** abbreviated paths cannot be passed directly to `cd`, `open`, or other filesystem commands.

## Install

With Cargo installed, run from the dotfiles repository root:

```sh
cargo install --path tools/shortpath --locked
shortpath --help
```

## Examples

**Shorten a path.** For the examples below, assume this directory tree and no other siblings:

```text
.
├── projects
│   ├── payments
│   │   └── src
│   │       └── main.rs
│   └── payroll
│       └── src
│           └── main.rs
└── products
```

```sh
shortpath projects/payments/src/main.rs
# proj/paym/s/main.rs
```

`projects` needs `proj` to distinguish it from `products`; `payments` needs `paym` to distinguish it from `payroll`. Actual output depends on the sibling names on your filesystem, including entries you did not supply as input.

**Keep more context.** Require at least two characters per shortened component and retain the last two components in full:

```sh
shortpath --min-length 2 --keep 2 projects/payments/src/main.rs
# proj/paym/src/main.rs
```

**Read a list.** Without path arguments, read stdin and emit one label per input path in the same order:

```sh
printf '%s\n' projects/payments/src/main.rs projects/payroll/src/main.rs | shortpath
# proj/paym/s/main.rs
# proj/payr/s/main.rs
```

**Handle filenames containing newlines.** Use NUL-delimited records at both ends:

```sh
find . -type f -print0 | shortpath --null
```

## Options

```text
shortpath [OPTIONS] [--] [PATH ...]
```

| Option | Default | Effect |
| --- | --- | --- |
| `-m`, `--min-length N` | `1` | Keep at least N Unicode characters per shortened component; shorter names stay full. N must be positive. |
| `-k`, `--keep N` | `1` | Keep the last N normal path components in full. Use `0` to shorten the final component too. |
| `-0`, `--null` | Off | Read and write NUL-delimited records instead of lines. |
| `-h`, `--help` | | Print usage. |
| `-V`, `--version` | | Print version. |

Configuration is through command-line options; there is no config file. Use `--` before paths beginning with `-`. When path arguments are supplied, stdin is ignored. Quote paths containing spaces and let your shell expand `~`.

## Path behavior

**Uniqueness uses sibling names.** Comparisons are case-sensitive and include hidden entries, files, directories, and symlinks. A name that prefixes another sibling stays full: with `--keep 0`, `foo` beside `foobar` becomes `foo` and `foob`. Shortening never introduces `.` or `..`. A component stays full if its parent contains non-UTF-8 names.

**Paths keep their shape.** Relative paths stay relative. Roots, leading `.` components, `..` components, and trailing directory separators are retained using Rust's platform path semantics; repeated separators and interior `.` components may be normalized. Symlinks are not canonicalized, and lookups follow the original path. A dangling leaf symlink is accepted.

**Errors stay visible.** Paths must exist and be UTF-8. Empty paths, missing paths, unreadable directories, and invalid UTF-8 input records produce stderr diagnostics and a nonzero exit status; remaining records are still processed. Invalid arguments stop the command. Empty stdin succeeds without output. Use `--null` for argument paths containing newlines, too.

**Labels reflect a snapshot.** Each parent directory is read once per invocation. Labels can change when siblings are added or removed; do not use them as persistent identifiers or assume case-insensitive shell completion will resolve them.

## Development

Run the focused checks from the repository root:

```sh
cargo test --locked --manifest-path tools/shortpath/Cargo.toml
cargo check --locked --manifest-path tools/shortpath/Cargo.toml
cargo clippy --locked --manifest-path tools/shortpath/Cargo.toml --all-targets -- -D warnings
cargo fmt --manifest-path tools/shortpath/Cargo.toml --check
```

CI runs these checks on macOS and Linux. Tests exercise the real CLI with temporary directories, including sibling collisions, Unicode, hidden names, symlinks, and NUL-delimited input.
