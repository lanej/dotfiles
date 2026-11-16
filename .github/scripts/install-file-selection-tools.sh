#!/usr/bin/env bash
set -euo pipefail

if [[ $# != 1 || ($1 != history && $1 != editor) ]]; then
    echo 'Usage: install-file-selection-tools.sh history|editor' >&2
    exit 64
fi
mode=$1
: "${RUNNER_TEMP:?Set RUNNER_TEMP to the tools directory parent}"
: "${GITHUB_PATH:?Set GITHUB_PATH to the path export file}"

case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) nvim_platform=linux-x86_64; fzf_platform=linux_amd64 ;;
    Darwin-arm64) nvim_platform=macos-arm64; fzf_platform=darwin_arm64 ;;
    Darwin-x86_64) nvim_platform=macos-x86_64; fzf_platform=darwin_amd64 ;;
    *) echo 'Unsupported file-selection test platform' >&2; exit 1 ;;
esac

tools="$RUNNER_TEMP/file-selection-tools"
mkdir -p "$tools/bin"
if [[ $fzf_platform == linux_* ]]; then
    sudo apt-get update
    sudo apt-get install -y fd-find zsh
    ln -sf "$(command -v fdfind)" "$tools/bin/fd"
else
    brew install fd
fi

curl --fail --location --retry 3 "https://github.com/junegunn/fzf/releases/download/v0.59.0/fzf-0.59.0-$fzf_platform.tar.gz" | tar -xz -C "$tools/bin"
printf '%s\n' "$tools/bin" >> "$GITHUB_PATH"

if [[ $mode == editor ]]; then
    curl --fail --location --retry 3 "https://github.com/neovim/neovim/releases/download/v0.12.5/nvim-$nvim_platform.tar.gz" | tar -xz -C "$tools"
    printf '%s\n' "$tools/nvim-$nvim_platform/bin" >> "$GITHUB_PATH"
fi
