#!/usr/bin/env bash
set -euo pipefail

if ! command -v octo-manager >/dev/null 2>&1; then
    echo "octo-manager is required for coordinator PR work" >&2
    exit 1
fi

guides=$(cd "$(dirname "${BASH_SOURCE[0]}")/guides" && pwd -P)
dest=${1:-${PASEO_COORDINATOR_DIR:-$HOME/.local/share/paseo-coordinator}}
if [[ "$dest" -ef "$guides" ]]; then
    echo "choose an installation directory outside the canonical guides" >&2
    exit 1
fi
mkdir -p "$dest"
ln -sfn "$guides"/{README,INSTRUCTIONS,LESSONS,PR-WORKFLOW}.md "$dest/"
echo "coordinator guidance ready: $dest/PR-WORKFLOW.md"
