#!/usr/bin/env bash
# Apply generated component mappings without requiring the Python resolver.
set -euo pipefail

dotfiles=$1
setup_home=$2
table="$dotfiles/config/components-install.tsv"

safe_relative() {
    case "$1" in
        ''|/*|*/../*|../*|*/..|.|*/./*|./*|*/.|*//*|*\\*) return 1 ;;
        *) return 0 ;;
    esac
}

# Validate every source and destination before replacing any links.
destinations=()
while IFS=$'\t' read -r component source destination extra; do
    if [[ -z "$component" || -n "$extra" ]] || ! safe_relative "$source" || ! safe_relative "$destination"; then
        printf 'Invalid component installation row: %s\n' "$component" >&2
        exit 1
    fi
    if [[ ! -f "$dotfiles/$source" || -d "$setup_home/$destination" ]]; then
        printf 'Invalid component installation: %s -> %s\n' "$source" "$destination" >&2
        exit 1
    fi
    for previous in ${destinations[@]+"${destinations[@]}"}; do
        if [[ "$destination" == "$previous" || "$destination" == "$previous/"* || "$previous" == "$destination/"* ]]; then
            printf 'Overlapping component destination: %s\n' "$destination" >&2
            exit 1
        fi
    done
    destinations+=("$destination")
done < "$table"

while IFS=$'\t' read -r component source destination; do
    parent=${destination%/*}
    if [[ "$parent" == "$destination" ]]; then parent=.; fi
    mkdir -p "$setup_home/$parent"
    ln -fs "$dotfiles/$source" "$setup_home/$destination"
done < "$table"
