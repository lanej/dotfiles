#!/usr/bin/env bash
# Only run for PRs the human has explicitly authorized rebasing and merging.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
exec python3 "$here/merge-seq.py" "$@"
