#!/usr/bin/env bash
set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
dest=${1:-${PASEO_COORDINATOR_DIR:-$HOME/.local/share/paseo-coordinator}}

for retired in merge-seq.sh merge-seq.py resolve-golangci.py normalize-golangci.py; do
    if [[ -e "$dest/bin/$retired" || -L "$dest/bin/$retired" ]]; then
        echo "retired coordinator helper: $dest/bin/$retired; inspect and move it outside bin/, then retry" >&2
        exit 1
    fi
done
if ! command -v octo-manager >/dev/null 2>&1; then
    echo "octo-manager is required for coordinator PR work" >&2
    exit 1
fi

# Earlier installers seeded editable notes without recording template ownership.
# Match complete shipped blobs, including the read-first line an upgrade could prepend.
is_old_starter() {
    case "$1:$2" in
        README.md:c261dc1965b24a2d7b4b2e3d98cbc12a40fe677a | \
        README.md:5002e929561fb0461c10abb087af27625f79d9a8 | \
        README.md:7b6d0ad2f9e0d222c772632f0c1fa463d80ff363 | \
        INSTRUCTIONS.md:861e8935f8080baef2cff177da437365b640a33c | \
        INSTRUCTIONS.md:9da2b374c0fbb465e01c3605dfc58953fa9571c6 | \
        INSTRUCTIONS.md:62097d70e2e8aae36e43cbae2801262b0ff4e64c | \
        INSTRUCTIONS.md:9a7c78b13e251ac20bd66838fb3c6a5fe6cc9747 | \
        INSTRUCTIONS.md:51912235b6dd0b303ecfe4f42804f0f57438da7e | \
        INSTRUCTIONS.md:6a0f4f11da6899bd7d6dc7e66042760b65e1a51c | \
        INSTRUCTIONS.md:870d31c88db3071b9eb18708fece2c28fd06b754 | \
        LESSONS.md:0f1f27a41110409520cc119d81f4732eb4934eb4 | \
        LESSONS.md:58986526b62201ee880a503224a18e98031612d6) return 0 ;;
    esac
    return 1
}

mkdir -p "$dest"
if [[ ! -e "$dest/.git" ]]; then
    git -C "$dest" init -q -b main
fi

installed=()
for name in PR-WORKFLOW.md README.md INSTRUCTIONS.md LESSONS.md; do
    target="$dest/$name"
    template="$here/templates/$name"
    if ! git -C "$dest" diff --cached --quiet -- "$name"; then
        if [[ "$name" == PR-WORKFLOW.md ]]; then
            echo "preserve the staged change to $target before refreshing the managed workflow" >&2
            exit 1
        fi
        continue
    fi
    if [[ -L "$target" || ( -e "$target" && ! -f "$target" ) ]]; then
        if [[ "$name" == PR-WORKFLOW.md ]]; then
            echo "expected a regular file for the managed workflow: $target" >&2
            exit 1
        fi
        continue
    fi
    if ! cmp -s "$template" "$target"; then
        if [[ -e "$target" && "$name" != PR-WORKFLOW.md ]]; then
            blob=$(git -C "$here" hash-object --stdin < "$target")
            is_old_starter "$name" "$blob" || continue
        fi
        cp "$template" "$target"
    fi
    installed+=("$name")
done

# Include newly seeded files in the scoped commit without staging their contents.
# A failed commit leaves operator staging intact and can be retried.
git -C "$dest" add --intent-to-add -- "${installed[@]}"
if ! git -C "$dest" diff --quiet -- "${installed[@]}"; then
    git -C "$dest" commit --only -qm 'refresh coordinator guidance' -- "${installed[@]}"
fi
echo "coordinator guidance ready: $dest/PR-WORKFLOW.md"
