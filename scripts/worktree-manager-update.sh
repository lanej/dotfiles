#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
runtime_root=$root
# shellcheck source=scripts/lib/git-worktree-runtime.sh
source "$root/scripts/lib/git-worktree-runtime.sh"
manager_version() {
	python3 - "$root/bootstrap/tools.toml" <<'PYTHON'
import sys
import tomllib
with open(sys.argv[1], 'rb') as stream:
    print(tomllib.load(stream)['tools']['worktree-manager']['version'])
PYTHON
}
case ${1:-} in
	inventory | verify | checkpoint | restore)
		git_runtime_catalog
		selection=$(git_runtime_cache)/selected-source
		[[ ! -f $selection ]] || git_runtime_source "$(cat "$selection")"
		python3 "$root/scripts/worktree-manager-activation.py" "$1" "$runtime_version" "$(manager_version)"
		;;
	pull) bash "$root/scripts/pull-git-worktree-source.sh" ;;
	build)
		selection=$(git_runtime_cache)/selected-source
		[[ -s $selection ]] || {
			printf 'Run project-update pull worktree-manager before building\n' >&2
			exit 1
		}
		bash "$root/scripts/install-git-worktree-hooks.sh" --source "$(cat "$selection")"
		version=$(manager_version)
		sh "$root/scripts/install-worktree-manager" "$version"
		make -C "$root" git
		;;
	status | restart)
		git_version=null worktree_version=null
		if [[ -x $HOME/.local/bin/git ]]; then
			installed=$("$HOME/.local/bin/git" --version)
			if [[ $installed =~ ^git\ version\ [0-9]+\.[0-9]+\.[0-9]+\.worktree-hooks\.[0-9]+$ ]]; then git_version="\"$installed\""; fi
		fi
		if [[ -x $HOME/.local/bin/worktree ]]; then
			installed=$("$HOME/.local/bin/worktree" --version)
			if [[ $installed =~ ^worktree\ [0-9]+\.[0-9]+\.[0-9]+$ ]]; then worktree_version="\"$installed\""; fi
		fi
		if [[ $1 == status ]]; then
			printf '{"installed_versions":{"git":%s,"worktree":%s},"running_revision":null}\n' "$git_version" "$worktree_version"
		else
			git_runtime_catalog
			selection=$(git_runtime_cache)/selected-source
			[[ ! -f $selection ]] || git_runtime_source "$(cat "$selection")"
			if [[ $git_version != "\"git version $runtime_version\"" || $worktree_version != "\"worktree $(manager_version)\"" ]]; then
				printf 'Build the selected Git and worktree manager before activation\n' >&2
				exit 1
			fi
			python3 "$root/scripts/worktree-manager-activation.py" "$1" "$runtime_version" "$(manager_version)"
		fi
		# Each invocation loads its installed executable; neither CLI has a service.
		;;
	*)
		printf 'Usage: %s {pull|build|restart|status|inventory|checkpoint|restore|verify}\n' "$0" >&2
		exit 2
		;;
esac
