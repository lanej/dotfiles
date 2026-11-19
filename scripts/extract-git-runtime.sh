#!/usr/bin/env bash
set -euo pipefail
runtime_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$runtime_root/scripts/lib/git-worktree-runtime.sh"
[[ $# == 3 ]] || {
	printf 'Usage: %s ARCHIVE EMPTY_DIRECTORY SHA256\n' "$0" >&2
	exit 2
}
archive=$1 destination=$2 expected=$3
fail() {
	printf 'Git archive extraction failed: %s\n' "$*" >&2
	exit 1
}
command -v bsdtar >/dev/null || fail 'Install bsdtar (libarchive-tools on Debian/Ubuntu) before extracting Git'
[[ -d $destination && ! -L $destination ]] || fail 'Destination must be a real directory'
[[ -z $(find "$destination" -mindepth 1 -print -quit) ]] || fail 'Destination must be empty'
destination=$(cd "$destination" && pwd -P)
scratch=$(mktemp -d "${TMPDIR:-/tmp}/git-runtime-extract.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
cp "$archive" "$scratch/archive.tar.gz"
[[ $(git_runtime_sha256 "$scratch/archive.tar.gz") == "$expected" ]] || fail 'Archive changed before extraction'
# bsdtar keeps its traversal/symlink protections enabled; never use -P or -U.
bsdtar -tf "$scratch/archive.tar.gz" >"$scratch/names"
while IFS= read -r name; do
	case $name in
		/* | .. | ../* | */../* | */..) fail 'Archive path is outside the destination' ;;
	esac
done <"$scratch/names"
bsdtar -tvf "$scratch/archive.tar.gz" >"$scratch/types"
while IFS= read -r entry; do
	case ${entry:0:1} in
		- | d | l | h) ;;
		*) fail 'Archive contains a special file' ;;
	esac
done <"$scratch/types"
bsdtar -xf "$scratch/archive.tar.gz" -C "$destination" --no-same-owner --no-same-permissions
# Reject links that could redirect later validation or receipt writes outside staging.
find "$destination" -type l -print0 >"$scratch/links"
while IFS= read -r -d '' link; do
	target=$(readlink "$link")
	[[ $target != /* ]] || fail 'Archive link is outside the destination'
	parent=$(cd -P "${link%/*}/$(dirname "$target")" && pwd -P) || fail 'Archive link has an invalid target'
	[[ $parent == "$destination" || $parent == "$destination/"* ]] || fail 'Archive link is outside the destination'
	[[ -e $link ]] || fail 'Archive contains a dangling or cyclic link'
done <"$scratch/links"
