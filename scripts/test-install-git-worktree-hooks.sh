#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
real_archive=
if [[ $# == 2 && $1 == --archive ]]; then real_archive=$2; elif [[ $# != 0 ]]; then exit 2; fi
scratch=$(mktemp -d "${TMPDIR:-/tmp}/git-install-test.XXXXXXXX")
cleanup() {
    local result=$?
    if [[ $result != 0 && -f $scratch/output ]]; then cat "$scratch/output" >&2; fi
    rm -rf "$scratch"
    exit "$result"
}
trap cleanup EXIT
export HOME="$scratch/home with 'quotes" XDG_CACHE_HOME="$scratch/cache"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
mkdir -p "$HOME" "$scratch/checkout/scripts/lib" "$scratch/checkout/bootstrap" "$scratch/checkout/patches/git-worktree-hooks"
fixture="$scratch/checkout"
cp "$root/scripts/"{install-git-worktree-hooks.sh,pull-git-worktree-source.sh,extract-git-runtime.py} "$fixture/scripts/"
cp "$root/scripts/lib/git-worktree-runtime.sh" "$fixture/scripts/lib/"
cp "$root/bootstrap/tools.toml" "$fixture/bootstrap/"
cp "$root/patches/git-worktree-hooks/"*.patch "$fixture/patches/git-worktree-hooks/"
cat > "$fixture/scripts/build-git-worktree-hooks.sh" <<'BUILD'
#!/usr/bin/env bash
set -euo pipefail
runtime_root=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$runtime_root/scripts/lib/git-worktree-runtime.sh"
git_runtime_catalog
if [[ $# == 3 ]]; then git_runtime_source "$3"; fi
[[ ! -f $runtime_root/fail-build ]] || exit 9
printf 'build\n' >> "$runtime_root/builds"
mkdir -p "$1/stage/bin" "$1/stage/libexec/git-core" "$1/stage/share/git-core/templates/hooks"
stage="$1/stage"
cat > "$stage/bin/git" <<'GIT'
#!/bin/sh
runtime=$(cd "$(dirname "$0")/.." && pwd)
case $1 in
    --version) cat "$runtime/version" ;;
    --exec-path) printf '%s/libexec/git-core\n' "$runtime" ;;
    init) mkdir -p "$2/.git/hooks"; touch "$2/.git/hooks/pre-commit.sample" ;;
    *) exit 8 ;;
esac
GIT
printf 'git version %s\n' "$runtime_version" > "$stage/version"
printf '#!/bin/sh\necho "usage: git remote-curl" >&2\nexit 1\n' > "$stage/libexec/git-core/git-remote-http"
chmod +x "$stage/bin/git" "$stage/libexec/git-core/git-remote-http"
name=$(git_runtime_archive_name)
tar -czf "$1/$name" -C "$stage" .
printf '%s  %s\n' "$(git_runtime_sha256 "$1/$name")" "$name" > "$1/$name.sha256"
BUILD
install() { bash "$fixture/scripts/install-git-worktree-hooks.sh" "$@" > "$scratch/output" 2>&1; }
reject() {
    local reason=$1
    shift
    if install "$@"; then printf 'Unexpected successful installation\n' >&2; exit 1; fi
    if [[ -n $reason ]]; then grep -F "$reason" "$scratch/output"; fi
}
active="$HOME/.local/bin/git"
install
first=$(readlink "$active")
install
[[ $(wc -l < "$fixture/builds") == 1 && $(readlink "$active") == "$first" ]]
printf '\n# Changed build input\n' >> "$fixture/patches/git-worktree-hooks/0001-post-worktree.patch"
install
[[ $(wc -l < "$fixture/builds") == 2 && $(readlink "$active") != "$first" && -f $first ]]
current=$(readlink "$active")
touch "$fixture/fail-build"
printf '\n# Failing update\n' >> "$fixture/patches/git-worktree-hooks/0001-post-worktree.patch"
reject ''
[[ $(readlink "$active") == "$current" ]]
rm "$fixture/fail-build"
printf 'PASS CLI build reuse, changed inputs and failed-build preservation\n'

# Real local remotes exercise numeric stable selection, shallow clones and advancement.
git init -q "$scratch/upstream"
git -C "$scratch/upstream" config user.name Test
git -C "$scratch/upstream" config user.email test@example.invalid
git -C "$scratch/upstream" -c user.name=Test -c user.email=test@example.invalid commit -q --allow-empty -m initial
for tag in v1.9.9 v1.10.0 v9.0.0-rc1; do git -C "$scratch/upstream" tag "$tag"; done
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.file://$scratch/upstream.insteadOf" GIT_CONFIG_VALUE_0=https://github.com/git/git.git
bash "$fixture/scripts/pull-git-worktree-source.sh"
selected=$(cat "$XDG_CACHE_HOME/dotfiles/git-worktree-hooks/selected-source")
[[ $(git -C "$selected" describe --tags --exact-match) == v1.10.0 ]]
[[ $(git -C "$selected" rev-parse --is-shallow-repository) == true ]]
install
[[ $("$active" --version) == 'git version 1.10.0.worktree-hooks.1' ]]
git -C "$scratch/upstream" -c user.name=Test -c user.email=test@example.invalid commit -q --allow-empty -m next
git -C "$scratch/upstream" tag -a v1.11.0 -m stable
bash "$fixture/scripts/pull-git-worktree-source.sh"
install
[[ $("$active" --version) == 'git version 1.11.0.worktree-hooks.1' ]]
current=$(readlink "$active")
# A discovery failure must retain the selected source and active installation.
old_selection=$(cat "$XDG_CACHE_HOME/dotfiles/git-worktree-hooks/selected-source")
export GIT_CONFIG_KEY_0="url.file://$scratch/missing.insteadOf"
if bash "$fixture/scripts/pull-git-worktree-source.sh" > "$scratch/pull-error" 2>&1; then exit 1; fi
[[ $(readlink "$active") == "$current" && $(cat "$XDG_CACHE_HOME/dotfiles/git-worktree-hooks/selected-source") == "$old_selection" ]]
unset GIT_CONFIG_COUNT GIT_CONFIG_KEY_0 GIT_CONFIG_VALUE_0
printf 'PASS latest stable selection, RC exclusion, annotated tags, shallow clone and failed pull\n'

# The public archive path retains safety for explicit offline installation.
runtime_root=$fixture
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$fixture/scripts/lib/git-worktree-runtime.sh"
git_runtime_catalog
name=$(git_runtime_archive_name)
bash "$fixture/scripts/build-git-worktree-hooks.sh" "$scratch/archive"
archive="$scratch/archive/$name"
install --archive "$archive" --home "$scratch/offline"
printf '%064d  %s\n' 0 "$name" > "$archive.sha256"
reject 'checksum mismatch' --archive "$archive" --home "$scratch/bad-checksum"
printf '%s  %s\n' "$(git_runtime_sha256 "$archive")" "$name" > "$archive.sha256"
mkdir -p "$scratch/owned/.local/bin"
printf 'user-owned\n' > "$scratch/owned/.local/bin/git"
reject 'user-managed' --archive "$archive" --home "$scratch/owned"
[[ $(cat "$scratch/owned/.local/bin/git") == user-owned ]]
rm "$scratch/owned/.local/bin/git"
ln -s /usr/bin/git "$scratch/owned/.local/bin/git"
reject 'user-managed' --archive "$archive" --home "$scratch/owned"
[[ $(readlink "$scratch/owned/.local/bin/git") == /usr/bin/git ]]
printf 'PASS checksums and user-managed executables/symlinks\n'
printf 'git version wrong-version\n' > "$scratch/archive/stage/version"
tar -czf "$archive" -C "$scratch/archive/stage" .
printf '%s  %s\n' "$(git_runtime_sha256 "$archive")" "$name" > "$archive.sha256"
reject 'runtime version' --archive "$archive" --home "$scratch/wrong-version"
printf 'git version %s\n' "$runtime_version" > "$scratch/archive/stage/version"
printf '#!/bin/sh\necho "fixture loader failure" >&2\nexit 127\n' > "$scratch/archive/stage/libexec/git-core/git-remote-http"
tar -czf "$archive" -C "$scratch/archive/stage" .
printf '%s  %s\n' "$(git_runtime_sha256 "$archive")" "$name" > "$archive.sha256"
reject 'HTTPS helper cannot run' --archive "$archive" --home "$scratch/incompatible"
printf 'PASS wrong-version and incompatible transport rejection\n'


# Unsafe tar members are data fixtures; Python's archive library creates them.
python3 - "$archive" <<'PY'
import io
import sys
import tarfile
with tarfile.open(sys.argv[1], 'w:gz') as stream:
    member = tarfile.TarInfo('../escape')
    member.size = 1
    stream.addfile(member, io.BytesIO(b'x'))
PY
printf '%s  %s\n' "$(git_runtime_sha256 "$archive")" "$name" > "$archive.sha256"
reject 'outside the destination' --archive "$archive" --home "$scratch/unsafe"
[[ ! -e $scratch/unsafe/.local/opt/git-worktree-hooks/escape ]]
printf 'PASS unsafe archive extraction\n'

if [[ -n $real_archive ]]; then
    bash "$root/scripts/install-git-worktree-hooks.sh" --archive "$real_archive" --home "$scratch/real home with 'quotes"
    actual="$scratch/real home with 'quotes/.local/bin/git"
    [[ $("$actual" --version) == "git version $runtime_version" ]]
    bash "$root/scripts/install-git-worktree-hooks.sh" --archive "$real_archive" --home "$scratch/real home with 'quotes"
    printf 'PASS real runtime relocation, helpers, templates and quoted launcher\n'
else
    printf 'SKIP real runtime relocation (pass --archive)\n'
fi
