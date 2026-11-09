#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'HELP'
Usage: scripts/build-git-worktree-hooks.sh OUTPUT_DIRECTORY

Download the catalog-pinned Git source, apply the checked-in worktree hook patches, build
and test its runtime, then write a relocatable platform archive and checksum.
Requires Python 3.11+, a C toolchain, make, curl, Git, Perl, tar/xz, and development libraries
for zlib, libcurl and expat. Does not install Git or change PATH.
Set JOBS to control build parallelism (default: 4).
HELP
}

if [[ ${1:-} == --help || ${1:-} == -h ]]; then
    usage
    exit 0
fi
if [[ $# != 1 ]]; then
    usage >&2
    exit 2
fi

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
catalog_values=$(python3 - "$repo_root/bootstrap/tools.toml" <<'PYTHON'
import sys
import tomllib
with open(sys.argv[1], "rb") as stream:
    recipe = tomllib.load(stream)["tools"]["git-worktree-hooks"]
for key in ("version", "runtime_version", "source_sha256"):
    print(recipe[key])
PYTHON
)
version=$(printf '%s\n' "$catalog_values" | sed -n '1p')
runtime_version=$(printf '%s\n' "$catalog_values" | sed -n '2p')
source_sha256=$(printf '%s\n' "$catalog_values" | sed -n '3p')
source_url="https://www.kernel.org/pub/software/scm/git/git-$version.tar.xz"
jobs=${JOBS:-4}
if [[ ! $jobs =~ ^[1-9][0-9]*$ ]]; then
    printf 'JOBS must be a positive integer\n' >&2
    exit 2
fi
case $(uname -s) in
    Darwin) platform=darwin ;;
    Linux) platform=linux ;;
    *) printf 'Unsupported build platform\n' >&2; exit 2 ;;
esac
architecture=$(uname -m)
package="git-$version-worktree-hooks-$platform-$architecture"
mkdir -p "$1"
output=$(cd "$1" && pwd)
if [[ -e $output/$package.tar.gz || -e $output/$package.tar.gz.sha256 ]]; then
    printf 'Output already exists: %s\n' "$output/$package.tar.gz" >&2
    exit 2
fi
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
scratch=$(mktemp -d "${TMPDIR:-/tmp}/git-worktree-build.XXXXXXXX")
trap 'rm -rf "$scratch"' EXIT

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    else
        shasum -a 256 "$1" | cut -d ' ' -f 1
    fi
}

curl --fail --location --retry 3 "$source_url" -o "$scratch/source.tar.xz"
actual_sha256=$(sha256 "$scratch/source.tar.xz")
if [[ $actual_sha256 != "$source_sha256" ]]; then
    printf 'Source checksum mismatch: expected %s, got %s\n' "$source_sha256" "$actual_sha256" >&2
    exit 1
fi
tar -xJf "$scratch/source.tar.xz" -C "$scratch"
source_dir="$scratch/git-$version"
mkdir "$scratch/patches"
cp "$repo_root"/patches/git-worktree-hooks/*.patch "$scratch/patches/"
for patch in "$scratch"/patches/*.patch; do
    git -C "$source_dir" apply --check "$patch"
    git -C "$source_dir" apply "$patch"
done

build_options=(
    prefix=/usr/local RUNTIME_PREFIX=YesPlease "GIT_VERSION=$runtime_version"
    NO_GETTEXT=YesPlease NO_TCLTK=YesPlease NO_RUST=YesPlease
    NO_OPENSSL=YesPlease
)
if [[ $platform == darwin ]]; then
    # WHY: Use SDK libraries rather than absolute paths to Homebrew libraries.
    build_options+=(NO_HOMEBREW=YesPlease NO_FINK=YesPlease NO_DARWIN_PORTS=YesPlease
        CURL_CONFIG=/usr/bin/curl-config CURL_CFLAGS= CURL_LDFLAGS=-lcurl)
fi
make -C "$source_dir" -j "$jobs" "${build_options[@]}" all
make -C "$source_dir/t" -j "$jobs" "${build_options[@]}" \
    T='t240*.sh t1350-config-hooks-path.sh t1800-hook.sh'
make -C "$source_dir" "${build_options[@]}" DESTDIR="$scratch/stage" install
runtime="$scratch/stage/usr/local"

mkdir -p "$runtime/share/doc/git-worktree-hooks"
cp "$source_dir/COPYING" "$runtime/share/doc/git-worktree-hooks/COPYING"
provenance="$runtime/share/doc/git-worktree-hooks/BUILD.txt"
{
    printf 'Git source: %s\nSHA256: %s\n' "$source_url" "$source_sha256"
    printf 'Build platform: %s %s\n' "$platform" "$architecture"
    printf 'Build options:'
    printf ' %s' "${build_options[@]}"
    printf '\nPatches (SHA256):\n'
    for patch in "$scratch"/patches/*.patch; do
        printf '%s  %s\n' "$(sha256 "$patch")" "$(basename "$patch")"
        cp "$patch" "$runtime/share/doc/git-worktree-hooks/"
    done
} > "$provenance"

# WHY: Exercise relocation and installed templates/helpers before packaging.
"$runtime/bin/git" --version
"$runtime/bin/git" init "$scratch/smoke"
"$runtime/bin/git" -C "$scratch/smoke" -c user.name=Build -c user.email=build@example.invalid commit --allow-empty -m smoke
cat > "$scratch/smoke/.git/hooks/pre-worktree" <<'HOOK'
#!/bin/sh
exit 1
HOOK
chmod +x "$scratch/smoke/.git/hooks/pre-worktree"
if "$runtime/bin/git" -C "$scratch/smoke" worktree add -b rejected "$scratch/smoke-linked"; then
    printf 'Installed pre-worktree hook failed to reject creation\n' >&2
    exit 1
fi
if [[ -e $scratch/smoke-linked ]] || "$runtime/bin/git" -C "$scratch/smoke" show-ref --verify --quiet refs/heads/rejected; then
    printf 'Rejected creation left checkout or branch state\n' >&2
    exit 1
fi
rm "$scratch/smoke/.git/hooks/pre-worktree"
cat > "$scratch/smoke/.git/hooks/post-worktree" <<'HOOK'
#!/bin/sh
printf '%s\n' "$1" >> "$(git rev-parse --git-common-dir)/worktree-events"
HOOK
chmod +x "$scratch/smoke/.git/hooks/post-worktree"
PATH="$runtime/bin:$PATH" "$runtime/bin/git" -C "$scratch/smoke" worktree add --no-checkout --detach "$scratch/smoke-linked"
PATH="$runtime/bin:$PATH" "$runtime/bin/git" -C "$scratch/smoke" worktree remove --force "$scratch/smoke-linked"
printf 'add\nremove\n' > "$scratch/expected-events"
cmp "$scratch/expected-events" "$scratch/smoke/.git/worktree-events"
if [[ $platform == darwin ]]; then
    otool -L "$runtime/bin/git" "$runtime/libexec/git-core/git-remote-http" > "$runtime/share/doc/git-worktree-hooks/libraries.txt"
    if grep -Eq '/opt/homebrew/|/usr/local/(opt|Cellar)/|/opt/local/' "$runtime/share/doc/git-worktree-hooks/libraries.txt"; then
        printf 'Runtime unexpectedly depends on package-manager libraries\n' >&2
        exit 1
    fi
else
    ldd "$runtime/bin/git" "$runtime/libexec/git-core/git-remote-http" > "$runtime/share/doc/git-worktree-hooks/libraries.txt"
fi
tar -czf "$scratch/$package.tar.gz" -C "$runtime" .
archive_sha256=$(sha256 "$scratch/$package.tar.gz")
printf '%s  %s.tar.gz\n' "$archive_sha256" "$package" > "$scratch/$package.tar.gz.sha256"
mv "$scratch/$package.tar.gz" "$scratch/$package.tar.gz.sha256" "$output/"
printf 'Built %s/%s.tar.gz\n' "$output" "$package"
