#!/bin/sh
set -eu

tools=$(mktemp -d)
tar -xzf "$OFFLINE_CI_INPUTS/pi.tar.gz" -C "$tools"
export PATH="$tools/pi:$PATH"
version=$(python3 -c 'import tomllib; print(tomllib.load(open("bootstrap/tools.toml", "rb"))["tools"]["pi"]["version"])')
test "$(pi --version)" = "$version"
exec python3 scripts/test-pi-resources.py --native
