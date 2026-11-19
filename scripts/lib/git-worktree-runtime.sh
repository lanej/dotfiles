#!/usr/bin/env bash
# Shared runtime naming and source checks for the Git build/install entrypoints.
# Callers provide runtime_root and consume the selected version/commit globals.
# shellcheck disable=SC2154,SC2034

git_runtime_catalog() {
    local values
    values=$(python3 - "$runtime_root/bootstrap/tools.toml" <<'PY'
import sys
import tomllib
with open(sys.argv[1], 'rb') as stream:
    recipe = tomllib.load(stream)['tools']['git-worktree-hooks']
print(recipe['version'])
print(recipe['runtime_version'])
PY
    ) || return 1
    catalog_version=$(printf '%s\n' "$values" | sed -n '1p')
    runtime_suffix=${values##*$'\n'}
    runtime_suffix=${runtime_suffix#"$catalog_version"}
    [[ $catalog_version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ && $runtime_suffix =~ ^\.worktree-hooks\.[0-9]+$ ]] || {
        printf 'Invalid Git version in catalog\n' >&2; return 1;
    }
    version=$catalog_version
    runtime_version=$version$runtime_suffix
    source_commit=
}

git_runtime_source() {
    local tag
    tag=$(git -C "$1" describe --tags --exact-match HEAD) || return 1
    [[ $tag =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { printf 'Source must be a stable Git release tag\n' >&2; return 1; }
    [[ -z $(git -C "$1" status --porcelain --untracked-files=all) ]] || { printf 'Preserve modified Git source before building\n' >&2; return 1; }
    version=${tag#v}
    runtime_version=$version$runtime_suffix
    source_commit=$(git -C "$1" rev-parse HEAD)
}

git_runtime_archive_name() {
    local system architecture
    case $(uname -s) in
        Darwin) system=darwin ;;
        Linux)
            system=linux
            if [[ -r /etc/os-release ]]; then
                # shellcheck disable=SC1091
                . /etc/os-release
                case " ${ID:-} ${ID_LIKE:-} " in
                    *' rhel '*|*' centos '*|*' rocky '*|*' almalinux '*|*' ol '*)
                        [[ ${VERSION_ID%%.*} != 8 ]] || system=linux-el8 ;;
                esac
            fi ;;
        *) printf 'Unsupported build platform\n' >&2; return 1 ;;
    esac
    architecture=$(uname -m)
    printf 'git-%s-worktree-hooks-%s-%s.tar.gz\n' "$version" "$system" "$architecture"
}

git_runtime_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d ' ' -f 1
    else
        shasum -a 256 "$1" | cut -d ' ' -f 1
    fi
}

git_runtime_cache() {
    printf '%s/dotfiles/git-worktree-hooks\n' "${XDG_CACHE_HOME:-$HOME/.cache}"
}
