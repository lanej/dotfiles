#!/usr/bin/env bash
set -eu

dotfiles=$1
shift
result=0
"$dotfiles/bin/project-update" update "$@" || result=$?
exit "$result"
