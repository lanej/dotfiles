#!/bin/bash
set -euo pipefail

checkout=$(cd -P -- "$(/usr/bin/dirname "${BASH_SOURCE[0]}")/.." && pwd)
release=$checkout/zellij/target/release
/bin/mkdir -p "$release"
started=$(/usr/bin/mktemp "$release/.lane-zellij-build-start.XXXXXX")
trap '/bin/rm -f "$started"' EXIT

cargo build --locked --release --manifest-path "$checkout/zellij/Cargo.toml" \
    --target-dir "$checkout/zellij/target" -p lane-zellij

# A pre-build timestamp keeps edits during compilation visible to the next request.
# Concurrent older stamps can only cause another check, never hide an unbuilt edit.
/bin/mv -f "$started" "$release/.lane-zellij-build-checked"
