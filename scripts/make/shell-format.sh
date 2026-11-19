#!/usr/bin/env bash
set -euo pipefail
dotfiles=$1
mode=$2
shift 2
cd "$dotfiles"
version=$(
	python3 - "$dotfiles/bootstrap/tools.toml" <<'PY'
import sys
import tomllib
with open(sys.argv[1], 'rb') as stream:
    print(tomllib.load(stream)['tools']['shfmt']['version'])
PY
)
formatter=${SHFMT:-shfmt}
if ! command -v "$formatter" >/dev/null; then
	printf 'Run bash scripts/install-shfmt.sh before formatting shell files\n' >&2
	exit 1
fi
installed=$("$formatter" --version)
[[ ${installed#v} == "$version" ]] || {
	printf 'Expected shfmt %s; run bash scripts/install-shfmt.sh\n' "$version" >&2
	exit 1
}
case $mode in
	--check) option=-d ;;
	--write) option=-w ;;
	*)
		printf 'Expected --check or --write\n' >&2
		exit 2
		;;
esac
# Adopt formatting for this runtime and its touched shell entrypoints first.
if [[ $# == 0 ]]; then
	set -- bootstrap.sh \
		scripts/build-git-worktree-hooks.sh \
		scripts/extract-git-runtime.sh \
		scripts/install-git-worktree-hooks.sh \
		scripts/lib/git-worktree-runtime.sh \
		scripts/pull-git-worktree-source.sh \
		scripts/test-install-git-worktree-hooks.sh \
		scripts/worktree-manager-update.sh \
		scripts/install-shfmt.sh \
		scripts/make/shell-format.sh \
		scripts/make/shellcheck.sh
fi
"$formatter" -ci -bn "$option" "$@"
