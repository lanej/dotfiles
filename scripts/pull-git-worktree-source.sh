#!/usr/bin/env bash
set -euo pipefail
runtime_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$runtime_root/scripts/lib/git-worktree-runtime.sh"
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
source_url=https://github.com/git/git.git
cache=$(git_runtime_cache)
mkdir -p "$cache/sources"
scratch=$(mktemp -d "$cache/.pull.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
# Exact three-part version tags exclude release candidates and maintenance branches.
git ls-remote --tags --refs "$source_url" 'v[0-9]*' > "$scratch/tags"
version=$(sed -nE 's@^[[:xdigit:]]+[[:space:]]+refs/tags/v([0-9]+\.[0-9]+\.[0-9]+)$@\1@p' "$scratch/tags" |
    sort -t. -k1,1n -k2,2n -k3,3n | tail -1)
[[ -n $version ]] || { printf 'No stable Git release tags found\n' >&2; exit 1; }
tag_hash=$(awk -v ref="refs/tags/v$version" '$2 == ref { print $1 }' "$scratch/tags")
[[ $tag_hash =~ ^[0-9a-f]{40,64}$ ]] || { printf 'Invalid upstream tag hash\n' >&2; exit 1; }
release_version=$version
source_dir="$cache/sources/$version-$tag_hash"
if [[ ! -d $source_dir ]]; then
    git clone --depth 1 --single-branch --branch "v$version" "$source_url" "$scratch/source"
    # Ref discovery and clone must describe the same release, even if a tag moves.
    [[ $(git -C "$scratch/source" rev-parse "refs/tags/v$version") == "$tag_hash" ]] || {
        printf 'Git release tag changed during pull; retry\n' >&2; exit 1;
    }
    mv "$scratch/source" "$source_dir"
fi
git_runtime_catalog
git_runtime_source "$source_dir"
[[ $version == "$release_version" ]] || { printf 'Cached Git source does not match selected release\n' >&2; exit 1; }
printf '%s\n' "$source_dir" > "$scratch/selected-source"
mv -f "$scratch/selected-source" "$cache/selected-source"
printf 'Selected stable Git %s (%s)\n' "$version" "$source_commit"
