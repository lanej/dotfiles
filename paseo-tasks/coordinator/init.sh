#!/usr/bin/env bash
# Create (or refresh) the Paseo coordinator memory repo.
#
# The coordinator's instructions, lessons, current state and helper scripts live in a
# local git repo (default: ~/.local/share/paseo-coordinator). This script is idempotent:
# it seeds missing files from templates/, never overwrites existing state, and always
# refreshes bin/ from this checkout (the source of truth for the scripts).
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
dest=${1:-${PASEO_COORDINATOR_DIR:-$HOME/.local/share/paseo-coordinator}}

# Refuse partial upgrades that would leave a competing merge engine installed.
for retired in merge-seq.sh merge-seq.py resolve-golangci.py normalize-golangci.py; do
    if [ -e "$dest/bin/$retired" ] || [ -L "$dest/bin/$retired" ]; then
        echo "retired coordinator helper: $dest/bin/$retired; inspect and preserve it outside bin/, remove the entry, then retry" >&2
        exit 1
    fi
done
if ! command -v octo-manager >/dev/null 2>&1; then
    echo "octo-manager is required for coordinator PR lifecycle work; install it before initialization" >&2
    exit 1
fi

mkdir -p "$dest/bin" "$dest/initiatives"

# Seed state files from templates only when absent.
for name in README.md INSTRUCTIONS.md LESSONS.md STATE.md; do
    [ -e "$dest/$name" ] || cp "$here/templates/$name" "$dest/$name"
done

# Scripts are code, not state: always refresh them from the dotfiles checkout.
cp "$here/bin/commit-state" "$dest/bin/commit-state"
chmod +x "$dest/bin/commit-state"
cp "$here/templates/PR-WORKFLOW.md" "$dest/PR-WORKFLOW.md"
policy='Read PR-WORKFLOW.md before PR work. It governs the PR lifecycle when older local instructions disagree.'
if ! grep -Fqx "$policy" "$dest/INSTRUCTIONS.md"; then
    updated=$(mktemp "$dest/.instructions.XXXXXX")
    { printf '%s\n\n' "$policy"; cat "$dest/INSTRUCTIONS.md"; } > "$updated"
    mv "$updated" "$dest/INSTRUCTIONS.md"
fi

if [ ! -d "$dest/.git" ]; then
    git -C "$dest" init -q -b main
fi

"$dest/bin/commit-state" "refresh coordinator scripts and seed missing state"
echo "coordinator state ready: $dest"
