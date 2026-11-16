#!/usr/bin/env bash
set -eu

dotfiles=$1
shift
result=0
"$dotfiles/bin/project-update" update "$@" || result=$?
if [ "$result" -eq 3 ]; then
    printf 'Updates installed; manual activation remains for the projects listed above.\n' >&2
    exit 0
fi
exit "$result"
