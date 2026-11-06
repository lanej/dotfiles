#!/usr/bin/env bash
set -euo pipefail

if gpg --list-secret-keys 6DAE70CE5C232C03 >/dev/null 2>&1; then
    echo "✓ GPG key 6DAE70CE5C232C03 already present"
else
    echo "Restoring GPG key from 1Password..."
    if ! command -v op >/dev/null 2>&1; then
        echo "Error: 1Password CLI (op) not found" >&2
        exit 1
    fi
    op read "op://Personal/d4xe37k5vnkkjmx5hk3vxiinn4/private_key" --account my.1password.com | gpg --import
    echo "✓ GPG key imported"
    echo ""
    echo "Now setting key trust level..."
    echo "Run the following commands:"
    echo "  gpg --edit-key 6DAE70CE5C232C03"
    echo "  trust"
    echo "  5 (ultimate)"
    echo "  y"
    echo "  quit"
fi
