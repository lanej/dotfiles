#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
values=$(
	python3 - "$root/bootstrap/tools.toml" <<'PY'
import sys
import tomllib
with open(sys.argv[1], 'rb') as stream:
    tools = tomllib.load(stream)['tools']
print(tools['shfmt']['version'])
print(tools['go']['version'])
PY
)
version=${values%%$'\n'*}
go_version=${values##*$'\n'}
if command -v shfmt >/dev/null; then
	installed=$(shfmt --version)
	if [[ ${installed#v} == "$version" ]]; then
		printf 'Using installed shfmt %s\n' "$version"
		exit 0
	fi
fi
# Reuse the catalog's Go provisioning and the bootstrap tool adapter.
# shellcheck source=bootstrap.sh
source "$root/bootstrap.sh"
install_package_version go "$go_version"
install_shfmt_from_release "$version"
printf 'Installed shfmt %s in %s/.local/bin\n' "$version" "$HOME"
