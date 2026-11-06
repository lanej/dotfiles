#!/usr/bin/env bash
set -euo pipefail

# WHY: Local checks and CI use reviewed versions without changing go.mod.
lint_version=2.13.2
vuln_version=v1.9.0
mode=${1:-all}
case "$mode" in
    all|lint|fmt|test|vuln|tools) ;;
    *) printf 'Usage: %s [all|lint|fmt|test|vuln|tools]\n' "$0" >&2; exit 2 ;;
esac
if [ "$#" -gt 1 ]; then
    printf 'Expected at most one check name.\n' >&2
    exit 2
fi

cd "$(dirname "${BASH_SOURCE[0]}")/.."
if [ ! -f go.mod ] || [ ! -f .golangci.yml ]; then
    printf 'Run from a project with go.mod and the committed .golangci.yml profile.\n' >&2
    exit 1
fi
command -v go >/dev/null || { printf 'Install the Go toolchain selected by go.mod.\n' >&2; exit 1; }
# WHY: A parent workspace must not replace dependencies that CI resolves alone.
export GOWORK=off
case "$(uname -s)" in
    Darwin) tool_os=darwin ;;
    Linux) tool_os=linux ;;
    *) printf 'Supported tool hosts: macOS and Linux.\n' >&2; exit 1 ;;
esac
case "$(uname -m)" in
    x86_64|amd64) tool_arch=amd64 ;;
    arm64|aarch64) tool_arch=arm64 ;;
    *) printf 'Supported tool architectures: amd64 and arm64.\n' >&2; exit 1 ;;
esac
cache_root=${XDG_CACHE_HOME:-$HOME/.cache}/go-quality
lint_dir=$cache_root/golangci-lint/$lint_version/$tool_os-$tool_arch
lint=$lint_dir/golangci-lint
# WHY: A govulncheck binary built by an older Go can misread newer packages.
# Go's host architecture can differ from uname under macOS Rosetta.
go_host_os=$(go env GOHOSTOS)
go_host_arch=$(go env GOHOSTARCH)
vuln_dir=$cache_root/govulncheck/$vuln_version/$(go env GOVERSION)/$go_host_os-$go_host_arch
vuln=$vuln_dir/govulncheck

install_lint() (
    [ ! -x "$lint" ] || exit 0
    mkdir -p "$lint_dir"
    stage=$(mktemp -d "$lint_dir/.download.XXXXXX")
    trap 'rm -rf "$stage"' EXIT
    package=golangci-lint-$lint_version-$tool_os-$tool_arch
    archive=$package.tar.gz
    release=https://github.com/golangci/golangci-lint/releases/download/v$lint_version
    curl -fsSL --retry 3 "$release/$archive" -o "$stage/$archive"
    curl -fsSL --retry 3 "$release/golangci-lint-$lint_version-checksums.txt" -o "$stage/checksums"
    checksum=$(awk -v archive="$archive" '$2 == archive { print $1 }' "$stage/checksums")
    if [ "${#checksum}" -ne 64 ] || [[ "$checksum" == *[!a-fA-F0-9]* ]]; then
        printf 'Missing or invalid checksum for %s.\n' "$archive" >&2
        exit 1
    fi
    printf '%s  %s\n' "$checksum" "$archive" > "$stage/selected-checksum"
    cd "$stage"
    if command -v sha256sum >/dev/null; then
        sha256sum -c selected-checksum
    else
        shasum -a 256 -c selected-checksum
    fi
    tar -xozf "$archive" "$package/golangci-lint"
    chmod 755 "$package/golangci-lint"
    mv "$package/golangci-lint" "$lint"
)

install_vuln() (
    [ ! -x "$vuln" ] || exit 0
    mkdir -p "$vuln_dir"
    stage=$(mktemp -d "$vuln_dir/.build.XXXXXX")
    trap 'rm -rf "$stage"' EXIT
    GOOS=$go_host_os GOARCH=$go_host_arch CGO_ENABLED=0 GOBIN=$stage \
        go install golang.org/x/vuln/cmd/govulncheck@"$vuln_version"
    mv "$stage/govulncheck" "$vuln"
)

if [ "$mode" = tools ] || [ "$mode" = lint ] || [ "$mode" = fmt ] || [ "$mode" = all ]; then
    install_lint
fi
if [ "$mode" = tools ]; then
    install_vuln
fi
if [ "$mode" = fmt ]; then
    "$lint" fmt --config .golangci.yml
fi
if [ "$mode" = lint ] || [ "$mode" = all ]; then
    "$lint" config verify --config .golangci.yml
    # WHY: fmt --diff reports changes without consistently failing on them.
    diff_file=$(mktemp)
    trap 'rm -f "$diff_file"' EXIT
    format_status=0
    "$lint" fmt --config .golangci.yml --diff > "$diff_file" || format_status=$?
    if [ -s "$diff_file" ]; then
        cat "$diff_file"
        printf 'Formatting differs; run scripts/check-go.sh fmt.\n' >&2
        exit 1
    fi
    if [ "$format_status" -ne 0 ]; then
        exit "$format_status"
    fi
    go mod tidy -diff
    "$lint" run --config .golangci.yml ./...
fi
if [ "$mode" = test ] || [ "$mode" = all ]; then
    if [ "$(go env CGO_ENABLED)" != 1 ]; then
        printf 'Race tests require CGO_ENABLED=1 and a C compiler.\n' >&2
        exit 1
    fi
    if command -v gotestsum >/dev/null; then
        gotestsum -- -race -count=1 ./...
    else
        go test -race -count=1 ./...
    fi
fi
if [ "$mode" = vuln ] || [ "$mode" = all ]; then
    install_vuln
    "$vuln" ./...
fi
