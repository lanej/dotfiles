#!/usr/bin/env bash
# Build only the opt-in native helper, never replace the installed kitten.
set -euo pipefail
root=$(cd -- "$(dirname -- "$0")/.." && pwd)
version=0.50.0
sha=01f20d0b253af0a7e041394a501adc83483f2eee01faf607a933c028343ab71a
out=${1:-${KITTY_CONFIG_DIRECTORY:-${XDG_CONFIG_HOME:-$HOME/.config}/kitty}/hint-native}
case "$out" in /*) ;; *) out="$PWD/$out";; esac
cache=${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles/kitty-native-hints/$version
mkdir -p "$cache" "$(dirname "$out")"
archive="$cache/kitty.tar.xz"
if [[ ! -f "$archive" ]]; then
    curl --fail --location --retry 3 "https://github.com/kovidgoyal/kitty/releases/download/v$version/kitty-$version.tar.xz" -o "$archive.tmp"
    mv "$archive.tmp" "$archive"
fi
actual=$(python3 -c 'import hashlib,sys;print(hashlib.file_digest(open(sys.argv[1],"rb"),"sha256").hexdigest())' "$archive")
if [[ "$actual" != "$sha" ]]; then
    echo "Kitty source checksum mismatch" >&2
    exit 1
fi
work=$(mktemp -d "$cache/build.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
tar -xJf "$archive" -C "$work" --strip-components=1
cd "$work"
# The installed, matching Kitty supplies the Python extension for upstream
# code generation. Import its packages before adding the source tree to sys.path.
kitty +runpy 'import kitty.fast_data_types as f, kittens, sys, os, pathlib; from kitty.constants import version; assert tuple(version)[:3] == (0, 50, 0); pathlib.Path("kitty/docs_ref_map_generated.h").write_text("static const char docs_ref_map[] = {" + ", ".join(map(str, f.get_docs_ref_map().rstrip(b"\\0"))) + "};\\n"); sys.path.insert(0, os.getcwd()); from gen.go_code import main; main()'
cp "$root/kitty/native-hints/styled.go" kittens/hints/dotfiles_styled.go
cp "$root/kitty/native-hints/styled_test.go" kittens/hints/dotfiles_styled_test.go
mkdir -p tools/cmd/dotfiles-hints
cp "$root/kitty/native-hints/main.go" tools/cmd/dotfiles-hints/main.go
gofmt -w kittens/hints/dotfiles_styled*.go tools/cmd/dotfiles-hints/main.go
go test ./kittens/hints -run '^TestDotfiles'
go build -trimpath -ldflags="-s -w" -o "$out.tmp" ./tools/cmd/dotfiles-hints
mv "$out.tmp" "$out"
echo "Installed native hints helper: $out"
