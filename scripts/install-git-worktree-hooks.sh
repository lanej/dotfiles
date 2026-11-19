#!/usr/bin/env bash
set -euo pipefail
runtime_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$runtime_root/scripts/lib/git-worktree-runtime.sh"
archive='' source_dir='' name_only=false
install_home=$HOME
while [[ $# -gt 0 ]]; do
    case $1 in
        --archive) archive=$2; shift 2 ;;
        --source) source_dir=$2; shift 2 ;;
        --home) install_home=$2; shift 2 ;;
        --archive-name) name_only=true; shift ;;
        *) printf 'Usage: %s [--home DIR] [--source DIR] [--archive FILE] [--archive-name]\n' "$0" >&2; exit 2 ;;
    esac
done
git_runtime_catalog
if [[ -z $source_dir && -z $archive && $name_only == false ]]; then
    selection=$(git_runtime_cache)/selected-source
    [[ ! -f $selection ]] || source_dir=$(cat "$selection")
fi
if [[ -n $source_dir ]]; then
    source_dir=$(cd "$source_dir" && pwd -P)
    git_runtime_source "$source_dir"
fi
name=$(git_runtime_archive_name)
if $name_only; then printf '%s\n' "$name"; exit 0; fi
mkdir -p "$install_home"
install_home=$(cd "$install_home" && pwd -P)
installs="$install_home/.local/opt/git-worktree-hooks"
active="$install_home/.local/bin/git"
fail() { printf 'Git runtime install failed: %s\n' "$*" >&2; exit 1; }
managed_link() {
    local target parent
    [[ -e $active || -L $active ]] || return 0
    [[ -L $active ]] || return 1
    target=$(readlink "$active")
    [[ $target == /* ]] || target="${active%/*}/$target"
    parent=$(cd "${target%/*}" 2>/dev/null && pwd -P) || return 1
    [[ ${parent%/*/*} == "$installs" && ${parent##*/} == bin ]] || return 1
    [[ ${target##*/} == git || ${target##*/} == git-launcher ]] || return 1
    [[ -f ${parent%/*}/.archive-sha256 ]]
}
validate() (
    local variable helpers message result smoke
    for variable in ${!GIT_@}; do unset "$variable"; done
    export HOME="$install_home" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 LC_ALL=C
    result=$("$1/bin/git" --version) || return 1
    [[ $result == "git version $runtime_version" ]] || { printf 'Archive runtime version does not match selected source\n' >&2; return 1; }
    helpers=$("$1/bin/git" --exec-path) || return 1
    [[ $helpers == "$1/libexec/git-core" ]] || { printf 'Git helpers did not relocate\n' >&2; return 1; }
    [[ -x $helpers/git-remote-http ]] || { printf 'Archive is missing the HTTPS helper\n' >&2; return 1; }
    result=0
    message=$("$helpers/git-remote-http" 2>&1) || result=$?
    [[ $result == 1 && $message == *'usage: git remote-curl'* ]] || { printf 'HTTPS helper cannot run: %s\n' "$message" >&2; return 1; }
    smoke=$(mktemp -d "${TMPDIR:-/tmp}/git-install-smoke.XXXXXXXX") || return 1
    trap 'rm -rf "$smoke"' EXIT
    "$1/bin/git" init "$smoke" >/dev/null || return 1
    [[ -f $smoke/.git/hooks/pre-commit.sample ]] || { printf 'Git templates did not relocate\n' >&2; return 1; }
)
managed_link || fail "Refusing to replace user-managed executable or link: $active"
[[ ! -L $installs ]] || fail "Runtime directory must not be a symlink: $installs"
mkdir -p "$installs" "${active%/*}"
scratch=$(mktemp -d "$installs/.install.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT
source_identity() {
    {
        printf '%s\n%s\n%s\n' "$version" "$runtime_version" "$source_commit"
        for input in "$runtime_root/scripts/build-git-worktree-hooks.sh" "$runtime_root/scripts/lib/git-worktree-runtime.sh" "$runtime_root"/patches/git-worktree-hooks/*.patch; do
            printf '%s\n' "${input#"$runtime_root"/}"
            git_runtime_sha256 "$input"
        done
    } > "$scratch/inputs"
    git_runtime_sha256 "$scratch/inputs"
}
identity=
if [[ -z $archive ]]; then identity=$(source_identity); fi
destination="$installs/$runtime_version${identity:+-$identity}"
if [[ -z $archive && ! -e $destination ]]; then
    if [[ -n $source_dir ]]; then
        bash "$runtime_root/scripts/build-git-worktree-hooks.sh" "$scratch/build" --source "$source_dir"
    else
        bash "$runtime_root/scripts/build-git-worktree-hooks.sh" "$scratch/build"
    fi
    [[ $(source_identity) == "$identity" ]] || fail 'Git build inputs changed during compilation; retry'
    archive="$scratch/build/$name"
fi
digest=
if [[ -n $archive ]]; then
    generic=${name/-linux-el8-/-linux-}
    [[ ${archive##*/} == "$name" || ${archive##*/} == "$generic" ]] || fail "Expected platform archive $name"
    expected=$(awk -v name="${archive##*/}" '$2 == name || $2 == "*" name { hash=$1; count++ } END { if (count==1) print tolower(hash) }' "$archive.sha256")
    [[ $expected =~ ^[0-9a-f]{64}$ ]] || fail 'Checksum file must identify this archive exactly once'
    digest=$(git_runtime_sha256 "$archive")
    [[ $digest == "$expected" ]] || fail 'Archive checksum mismatch'
fi
if [[ -e $destination || -L $destination ]]; then
    [[ -d $destination && ! -L $destination ]] || fail "Existing runtime is not managed: $destination"
    installed_digest=$(cat "$destination/.archive-sha256")
    [[ $installed_digest =~ ^[0-9a-f]{64}$ && ( -z $digest || $digest == "$installed_digest" ) ]] || fail "Existing runtime is not the same managed archive: $destination"
    validate "$destination" || fail 'Existing runtime validation failed'
else
    mkdir "$scratch/runtime"
    python3 "$runtime_root/scripts/extract-git-runtime.py" "$archive" "$scratch/runtime" "$digest"
    validate "$scratch/runtime" || fail 'Staged runtime validation failed'
    printf '%s\n' "$digest" > "$scratch/runtime/.archive-sha256"
    mv "$scratch/runtime" "$destination"
    if ! validate "$destination"; then
        rm -rf "$destination"
        fail 'Installed runtime validation failed'
    fi
fi
# Single-quote the absolute executable path so spaces and quotes survive relocation.
quoted=${destination//\'/\'\\\'\'}
printf '#!/bin/sh\nexec '\''%s/bin/git'\'' "$@"\n' "$quoted" > "$scratch/git-launcher"
chmod 755 "$scratch/git-launcher"
mv -f "$scratch/git-launcher" "$destination/bin/git-launcher"
managed_link || fail "Refusing changed user-managed executable or link: $active"
ln -s "$destination/bin/git-launcher" "$scratch/git"
actual_exec=$(
    for variable in ${!GIT_@}; do unset "$variable"; done
    "$scratch/git" --exec-path
)
[[ $actual_exec == "$destination/libexec/git-core" ]] || fail 'Installed entrypoint cannot locate helpers'
mv -f "$scratch/git" "$active"
printf 'Activated %s -> %s/bin/git-launcher\n' "$active" "$destination"
