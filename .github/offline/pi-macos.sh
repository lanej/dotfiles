#!/bin/sh
set -eu

tools=$(mktemp -d)
tar -xzf "$OFFLINE_CI_INPUTS/pi.tar.gz" -C "$tools"
export PATH="$tools/pi:$PATH"
version=$(awk '
  /^\[tools\.pi\]$/ { pi = 1; next }
  /^\[/ { pi = 0 }
  pi && $1 == "version" && $2 == "=" { gsub(/"/, "", $3); print $3; exit }
' bootstrap/tools.toml)
test -n "$version"
test "$(pi --version)" = "$version"
exec python3 scripts/test-pi-resources.py --native
