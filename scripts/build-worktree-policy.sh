#!/bin/sh
set -eu
root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
output=${1:?Usage: build-worktree-policy.sh OUTPUT_DIRECTORY}
mkdir -p "$output"
output=$(CDPATH='' cd -- "$output" && pwd)
version=$(python3 -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1],"rb"))["tools"]["worktree-policy"]["version"])' "$root/bootstrap/tools.toml")
cd "$root/tools/worktree-policy"
system=${GOOS:-$(go env GOOS)}
architecture=${GOARCH:-$(go env GOARCH)}
name="git-worktree-policy-$system-$architecture"
CGO_ENABLED=0 go build -trimpath -ldflags "-s -w -X main.version=$version" -o "$output/$name" .
if command -v sha256sum >/dev/null 2>&1; then digest=$(sha256sum "$output/$name" | awk '{print $1}')
else digest=$(shasum -a 256 "$output/$name" | awk '{print $1}'); fi
printf '%s  %s\n' "$digest" "$name" > "$output/$name.sha256"
ln -fs "$name" "$output/git-worktree-policy"
printf '%s\n' "$output/$name"
