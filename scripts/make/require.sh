#!/usr/bin/env bash
set -eu

case "$1" in
    command)
        command -v "$2" >/dev/null 2>&1 || {
            printf 'Missing dependency: %s. Install it or add it to PATH, then rerun make.\n' "$2" >&2
            exit 1
        }
        ;;
    os)
        test "$2" = "$3" || {
            printf '%s: requires %s; detected %s.\n' "$4" "$2" "$3" >&2
            exit 1
        }
        ;;
    *) printf 'Unknown requirement: %s\n' "$1" >&2; exit 1 ;;
esac
