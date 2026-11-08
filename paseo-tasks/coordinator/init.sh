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

mkdir -p "$dest/bin" "$dest/initiatives"

# Seed state files from templates only when absent.
for name in README.md INSTRUCTIONS.md LESSONS.md STATE.md; do
    [ -e "$dest/$name" ] || cp "$here/templates/$name" "$dest/$name"
done

# Scripts are code, not state: always refresh them from the dotfiles checkout.
for script in commit-state merge-seq.sh resolve-golangci.py normalize-golangci.py; do
    cp "$here/bin/$script" "$dest/bin/$script"
done
chmod +x "$dest/bin/commit-state" "$dest/bin/merge-seq.sh"

if [ ! -d "$dest/.git" ]; then
    git -C "$dest" init -q -b main
fi

"$dest/bin/commit-state" "refresh coordinator scripts and seed missing state" || true
echo "coordinator state ready: $dest"
