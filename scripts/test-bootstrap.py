#!/usr/bin/env python3
"""One fresh-box bootstrap workflow; downloads and package managers are fixtures."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib


def test_compatibility(root):
    with tempfile.TemporaryDirectory(prefix="dotfiles-bootstrap-compatibility-") as temporary:
        home = Path(temporary)
        env = {**os.environ, "HOME": str(home)}
        for key in ("SSL_CERT_FILE", "SSL_CERT_DIR"):
            env.pop(key, None)

        def run(script, *, extra=None, success=True):
            result = subprocess.run(
                ["/bin/bash", "-c", 'source "$1"\n' + script, "bootstrap-test", str(root / "bootstrap.sh")],
                env={**env, **(extra or {})}, capture_output=True, text=True, timeout=30,
            )
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            return result

        python = home / "python3"
        python.write_text(f"#!{sys.executable}\n" + '''
import os
from pathlib import Path
import ssl
import sys
defaults = ssl.get_default_verify_paths()
ssl.get_default_verify_paths = lambda: defaults._replace(cafile=os.environ.get("TEST_DEFAULT_CA"))
Path.is_file = lambda self: str(self) == os.environ.get("TEST_SYSTEM_CA")
exec(sys.stdin.read())
''')
        python.chmod(0o755)
        trust = '''
os=linux
configure_python_ca_trust || exit
printf '%s\\n' "${SSL_CERT_FILE-unset}" "${SSL_CERT_DIR-unset}"
'''
        for bundle in ("/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/certs/ca-certificates.crt"):
            result = run(trust, extra={"PATH": f"{home}:{env['PATH']}", "TEST_SYSTEM_CA": bundle})
            assert result.stdout.splitlines() == [bundle, "unset"], result.stdout
        result = run(trust, extra={"PATH": f"{home}:{env['PATH']}", "TEST_DEFAULT_CA": "/existing/ca.pem"})
        assert result.stdout.splitlines() == ["unset", "unset"], result.stdout
        for setting, value in (("SSL_CERT_FILE", "/custom/ca.pem"), ("SSL_CERT_DIR", "/custom/certs")):
            result = run(trust, extra={setting: value})
            assert result.stdout.splitlines() == [
                value if setting == "SSL_CERT_FILE" else "unset",
                value if setting == "SSL_CERT_DIR" else "unset",
            ], result.stdout
        result = run(trust, extra={"PATH": f"{home}:{env['PATH']}"})
        assert result.stdout.splitlines() == ["unset", "unset"], result.stdout
        print("PASS Linux CA discovery preserves existing and explicit trust stores")

        result = run('''
os=linux
bun() { printf '%s\\n' "${TEST_BUN_VERSION:-1.4.5-canary}"; }
package_semver() { return 1; }
install_bun_from_release() { TEST_BUN_VERSION=$1; printf 'installed stable %s\\n' "$1"; }
install_package_version bun 1.4.5
''')
        assert "installed stable 1.4.5" in result.stdout, result.stdout
        print("PASS prerelease Bun does not satisfy a stable runtime minimum")

        npm_bin = home / "npm-bin"
        cargo_bin = home / ".cargo/bin"
        npm_bin.mkdir()
        cargo_bin.mkdir(parents=True)
        wrapper = npm_bin / "stylua"
        wrapper.write_text("#!/bin/sh\necho 'GLIBC_2.34 not found' >&2\nexit 1\n")
        wrapper.chmod(0o755)
        installer_fixtures = '''
os=linux
package_semver() { return 1; }
npm() {
    printf 'npm %s\\n' "$*" >> "$HOME/events"
    case "$*" in
        "list -g --depth=0 @johnnymorganz/stylua-bin") test -f "$HOME/npm-bin/stylua" ;;
        "uninstall -g @johnnymorganz/stylua-bin") rm "$HOME/npm-bin/stylua" ;;
        *) return 1 ;;
    esac
}
cargo() {
    printf 'cargo %s\\n' "$*" >> "$HOME/events"
    [ "${TEST_CARGO_FAIL:-0}" != 1 ] || return 1
    printf '#!/bin/sh\\necho "stylua 2.6.0"\\n' > "$HOME/.cargo/bin/stylua"
    chmod +x "$HOME/.cargo/bin/stylua"
}
'''
        path = {"PATH": f"{npm_bin}:{cargo_bin}:{env['PATH']}"}
        run(installer_fixtures + "\ninstall_package_version stylua 2.6.0", extra={**path, "TEST_CARGO_FAIL": "1"}, success=False)
        assert wrapper.exists(), "Failed source build removed the existing wrapper"
        result = run(installer_fixtures + "\ninstall_package_version stylua 2.6.0\nstylua --version", extra=path)
        assert result.stdout.strip().endswith("stylua 2.6.0"), result.stdout
        assert not wrapper.exists()
        events = (home / "events").read_text()
        assert "cargo install stylua --locked --version 2.6.0 --features lua54,luajit,luau" in events
        previous = events
        run(installer_fixtures + "\ninstall_package_version stylua 2.6.0", extra=path)
        assert (home / "events").read_text() == previous, "Rerun reinstalled working StyLua"
        result = run('''
os=macos
install_package_version() { test "$*" = "node 24"; }
npm() { printf '%s\\n' "$*"; }
install_stylua_from_release 2.6.0
''')
        assert result.stdout.strip() == "install -g @johnnymorganz/stylua-bin@2.6.0"
        print("PASS source-built Linux StyLua replaces the incompatible npm wrapper; macOS retains npm")

        luacheck_fixtures = '''
command() {
    case "$*" in
        "-v brew"|"-v apt-get"|"-v pacman") return 1 ;;
        "-v dnf") return 0 ;;
        *) builtin command "$@" ;;
    esac
}
sudo() {
    printf '%s\\n' "$*" >> "$HOME/events"
    [ "${TEST_DNF_FAIL:-0}" != 1 ]
}
luarocks() {
    printf 'luarocks %s\\n' "$*" >> "$HOME/events"
    [ "${TEST_LUAROCKS_FAIL:-0}" != 1 ] || return 1
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/sh\\necho "Luacheck: 1.2.0"\\n' > "$HOME/.local/bin/luacheck"
    chmod +x "$HOME/.local/bin/luacheck"
}
install_luacheck_package
'''
        run(luacheck_fixtures, extra={"TEST_DNF_FAIL": "1"}, success=False)
        assert not (home / ".local/bin/luacheck").exists()
        run(luacheck_fixtures, extra={"TEST_LUAROCKS_FAIL": "1"}, success=False)
        assert not (home / ".local/bin/luacheck").exists()
        result = run(luacheck_fixtures)
        assert result.stdout.strip() == "Luacheck: 1.2.0"
        events = (home / "events").read_text()
        assert "dnf install -y luarocks lua-devel" in events
        assert f"luarocks install --tree {home}/.local luacheck" in events
        print("PASS DNF Luacheck installs through LuaRocks and propagates package failures")

        bsdtar_fixtures = '''
command() {
    case "$*" in
        "-v bsdtar") test -x "$HOME/.local/bin/bsdtar" ;;
        "-v brew") return 1 ;;
        "-v dnf") return 0 ;;
        *) builtin command "$@" ;;
    esac
}
source() {
    if [ "$1" = /etc/os-release ]; then
        ID=${TEST_OS_ID:-rocky}
    else
        builtin source "$@"
    fi
}
uname() { printf '%s\\n' "${TEST_ARCH:-x86_64}"; }
rpm() {
    printf 'rpm %s\\n' "$*" >> "$HOME/events"
    case "$1" in
        -q) printf '%s\\n' "${TEST_LIBARCHIVE:-3.3.3 3.el8_5 x86_64}" ;;
        --checksig)
            printf '%s: %s\\n' "$2" "${TEST_SIGNATURE:-digests signatures OK}"
            ;;
        -qp) printf '%s\\n' "${TEST_RPM_IDENTITY:-bsdtar-3.3.3-3.el8_5.x86_64}" ;;
        *) return 1 ;;
    esac
}
curl() {
    printf 'curl %s\\n' "$*" >> "$HOME/events"
    [ "${TEST_DOWNLOAD_FAIL:-0}" != 1 ] || return 1
    while [ "$#" -gt 0 ]; do
        if [ "$1" = -o ]; then
            printf 'fixture rpm\\n' > "$2"
            return
        fi
        shift
    done
    return 1
}
sudo() {
    printf 'sudo %s\\n' "$*" >> "$HOME/events"
    if [ "$*" = "dnf install -y bsdtar" ]; then
        [ "${TEST_DNF_MATCH:-0}" = 1 ] || return 1
    else
        [ "$1 $2 $3 $4" = "dnf install -y --setopt=localpkg_gpgcheck=1" ] || return 1
        [ -f "$5" ] || return 1
        [ "${TEST_INSTALL_FAIL:-0}" != 1 ] || return 1
    fi
    mkdir -p "$HOME/.local/bin"
    printf '#!/bin/sh\\nprintf "bsdtar fixture\\\\n"\\n' > "$HOME/.local/bin/bsdtar"
    chmod +x "$HOME/.local/bin/bsdtar"
}
install_from_package_manager bsdtar
'''
        package_home = home / "bsdtar"
        package_home.mkdir()
        package_env = {"HOME": str(package_home), "TMPDIR": str(package_home)}
        result = run(bsdtar_fixtures, extra=package_env)
        installed_tool = package_home / ".local/bin/bsdtar"
        assert subprocess.check_output([installed_tool], text=True) == "bsdtar fixture\n"
        events = (package_home / "events").read_text()
        assert "https://dl.rockylinux.org/vault/rocky/8.5/BaseOS/x86_64/os/Packages/b/bsdtar-3.3.3-3.el8_5.x86_64.rpm" in events
        assert "--setopt=localpkg_gpgcheck=1" in events
        assert not list(package_home.glob("dotfiles-bsdtar.*")), "Downloaded RPM scratch was retained"
        previous = events
        run(bsdtar_fixtures, extra=package_env)
        assert (package_home / "events").read_text() == previous, "Rerun reinstalled bsdtar"
        installed_tool.unlink()
        for failure in (
            {"TEST_SIGNATURE": "digests OK"},
            {"TEST_SIGNATURE": "digests SIGNATURES NOT OK"},
            {"TEST_SIGNATURE": "digests SIGNATURES NOT OK (NOKEY)"},
            {"TEST_RPM_IDENTITY": "bsdtar-3.3.3-3.el8_5.aarch64"},
            {"TEST_DOWNLOAD_FAIL": "1"},
            {"TEST_INSTALL_FAIL": "1"},
            {"TEST_OS_ID": "fedora"},
            {"TEST_LIBARCHIVE": "3.3.3 5.el8 x86_64"},
        ):
            run(bsdtar_fixtures, extra={**package_env, **failure}, success=False)
            assert not installed_tool.exists(), f"Unsafe or failed archive installed a tool: {failure}"
            assert not list(package_home.glob("dotfiles-bsdtar.*")), failure
        result = run(bsdtar_fixtures, extra={
            **package_env,
            "TEST_ARCH": "aarch64",
            "TEST_LIBARCHIVE": "3.4.0 2.el9_3 aarch64",
            "TEST_RPM_IDENTITY": "bsdtar-3.4.0-2.el9_3.aarch64",
        })
        assert installed_tool.is_file()
        events = (package_home / "events").read_text()
        assert "https://dl.rockylinux.org/vault/rocky/9.3/BaseOS/aarch64/os/Packages/b/bsdtar-3.4.0-2.el9_3.aarch64.rpm" in events
        installed_tool.unlink()
        (package_home / "events").unlink()
        run(bsdtar_fixtures, extra={**package_env, "TEST_DNF_MATCH": "1"})
        assert installed_tool.is_file()
        assert "curl " not in (package_home / "events").read_text()
        print("PASS pinned Rocky libarchive gets a matching signed bsdtar; untrusted archives and failures are rejected")


def test_go_path_precedence(root):
    with tempfile.TemporaryDirectory(prefix="dotfiles-bootstrap-go-path-") as temporary:
        for custom_gobin in (False, True):
            home = Path(temporary) / ("custom-gobin" if custom_gobin else "default-gopath")
            local_bin = home / ".local/bin"
            go_bin = home / ("custom-bin" if custom_gobin else "go-primary/bin")
            local_bin.mkdir(parents=True)
            go_bin.mkdir(parents=True)
            old_shfmt = go_bin / "shfmt"
            old_shfmt.write_text("#!/bin/sh\nprintf 'v3.10.0\\n'\n")
            old_shfmt.chmod(0o755)
            go_tool = go_bin / "go-only"
            go_tool.write_text("#!/bin/sh\nprintf 'Go tool available\\n'\n")
            go_tool.chmod(0o755)
            env = {
                **os.environ,
                "HOME": str(home),
                "PATH": "/usr/bin:/bin",
                "GOPATH": os.pathsep.join((str(home / "go-primary"), str(home / "go-secondary"))),
            }
            env.pop("GOBIN", None)
            env.pop("NVM_BIN", None)
            if custom_gobin:
                env["GOBIN"] = str(go_bin)
                nvm_bin = home / ".nvm/versions/node/v24.0.0/bin"
                nvm_bin.mkdir(parents=True)
                for node_bin, version in ((local_bin, "v22.23.3"), (nvm_bin, "v24.0.0")):
                    node = node_bin / "node"
                    node.write_text(f"#!/bin/sh\nprintf '{version}\\n'\n")
                    node.chmod(0o755)
                (home / ".nvm/nvm.sh").write_text(
                    'export NVM_BIN="$HOME/.nvm/versions/node/v24.0.0/bin"\n'
                )
            result = subprocess.run(
                ["/bin/bash", "-c", '''
set -e
source "$1"
go() {
    case "$*" in
        version) printf 'go version go1.26.2 linux/amd64\\n' ;;
        "env GOBIN") printf '%s\\n' "${GOBIN:-}" ;;
        "env GOPATH") printf '%s\\n' "$GOPATH" ;;
        "install mvdan.cc/sh/v3/cmd/shfmt@v3.14.1")
            printf '#!/bin/sh\\nprintf "v3.14.1\\\\n"\\n' > "$GOBIN/shfmt"
            chmod +x "$GOBIN/shfmt"
            ;;
        *) printf 'Unexpected Go command: %s\\n' "$*" >&2; return 1 ;;
    esac
}
install_config_runtime() { :; }
load_dotfiles_config() {
    DOTFILES_TOOLS=go,shfmt
    DOTFILES_INSTALL_PLAN=$'go\\tgo\\tgo\\t1.26.2\\nshfmt\\tpackage\\tshfmt\\t3.14.1'
}
package_semver() { return 1; }
run_configured_hooks() { :; }
make() { :; }
post_install_setup() { :; }
bootstrap_dotfiles install
printf 'Selected shfmt: %s\\n' "$(command -v shfmt)"
shfmt --version
go-only
if [ -n "${NVM_BIN:-}" ]; then node --version; fi
''', "bootstrap-go-path-test", str(root / "bootstrap.sh")],
                env=env, capture_output=True, text=True, timeout=10,
            )
            assert result.returncode == 0, (
                f"Go PATH setup failed (custom GOBIN={custom_gobin}):\n"
                + result.stdout + result.stderr
            )
            expected = [f"Selected shfmt: {local_bin / 'shfmt'}", "v3.14.1", "Go tool available"]
            if custom_gobin:
                expected.append("v24.0.0")
            assert result.stdout.splitlines()[-len(expected):] == expected, result.stdout
            assert old_shfmt.read_text() == "#!/bin/sh\nprintf 'v3.10.0\\n'\n"
        print("PASS selected NVM and installed tools precede older Go binaries; default GOPATH and custom GOBIN remain available")


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compatibility-only", action="store_true")
    options = parser.parse_args()
    test_compatibility(root)
    test_go_path_precedence(root)
    if options.compatibility_only:
        return
    with tempfile.TemporaryDirectory(prefix="dotfiles-bootstrap-") as temporary:
        home = Path(temporary)
        router_binary = home / ".codex/bedrock-router/bedrock-router"
        router_binary.parent.mkdir(parents=True)
        router_binary.write_bytes(b"externally installed router")
        router_config = home / ".codex/bedrock-router/config.json"
        router_config.write_bytes(b"external router configuration")
        router_state = home / ".codex/bedrock-router/sessions.sqlite3"
        router_state.write_bytes(b"external session database")
        fixture = home / "fixture"
        fixture.mkdir()
        # Model the unmanaged executable left by the previous runtime installer.
        installed = home / ".local/bin/zellij"
        installed.parent.mkdir(parents=True)
        installed.write_text('#!/bin/sh\necho "zellij 0.45.1"\n')
        installed.chmod(0o755)
        checkout = home / ".files"
        checkout.mkdir()
        (checkout / ".git/hooks").mkdir(parents=True)
        shutil.copytree(root / "git", checkout / "git")
        shutil.copyfile(root / "bootstrap.sh", checkout / "bootstrap.sh")
        shutil.copyfile(root / "Makefile", checkout / "Makefile")
        shutil.copytree(root / "config", checkout / "config")
        shutil.copytree(root / "bootstrap", checkout / "bootstrap")
        (checkout / "scripts").mkdir()
        shutil.copyfile(root / "scripts/install-pi", checkout / "scripts/install-pi")
        shutil.copyfile(root / "scripts/dotfiles-config.py", checkout / "scripts/dotfiles-config.py")
        shutil.copyfile(root / "scripts/runtime_requirements.py", checkout / "scripts/runtime_requirements.py")
        (checkout / "scripts/prepare-project-runtimes.py").write_text(
            'import json, pathlib, sys\n'
            'pathlib.Path(sys.argv[sys.argv.index("--output")+1]).write_text(json.dumps({"projects": {}}))\n')
        (checkout / "scripts/install-approval-cli.py").write_text("from pathlib import Path\nimport os, sys\nPath(os.environ['HOME'], sys.argv[1] + '-installed').touch()\n")
        (checkout / "scripts/install-studio.py").write_text("from pathlib import Path\nimport os\nhome = Path(os.environ['HOME'])\n(home / 'studio-installed').touch()\nwith (home / 'events').open('a') as log: log.write('studio install\\n')\n")
        shutil.copyfile(root / "scripts/install-treehouse", checkout / "scripts/install-treehouse")
        (checkout / "scripts/install-worktree-policy").write_text('#!/bin/sh\n[ "$1" = 0.1.1 ] || exit 1\ntouch "$HOME/native-policy-installed"\n')
        manager_version = tomllib.loads((root / "bootstrap/tools.toml").read_text())["tools"]["worktree-manager"]["version"]
        (checkout / "scripts/install-worktree-manager").write_text('#!/bin/sh\n[ "$1" = ' + manager_version + ' ] || exit 1\ntouch "$HOME/worktree-manager-installed"\n')
        (checkout / "scripts/install-git-worktree-hooks.sh").write_text(
            '#!/bin/sh\ntouch "$HOME/patched-git-installed"\n')
        shutil.copyfile(root / "scripts/setup-checklist.sh", checkout / "scripts/setup-checklist.sh")
        machine_config = home / ".config/dotfiles/config.toml"
        machine_config.parent.mkdir(parents=True)
        # Bootstrap must work before the machine's TOML is valid or Python is
        # available. The full stage will consume the repaired configuration.
        machine_config.write_text('sets = ["not-a-set"]\n')
        shutil.copytree(root / "scripts/make", checkout / "scripts/make")
        shutil.copyfile(root / "scripts/install-zellij", checkout / "scripts/install-zellij")
        shutil.copyfile(root / "scripts/install-zellij-navigation.py", checkout / "scripts/install-zellij-navigation.py")
        shutil.copytree(root / "zellij/navigation", checkout / "zellij/navigation")
        shutil.copyfile(root / "scripts/install-zellij-command-prompt.py", checkout / "scripts/install-zellij-command-prompt.py")
        shutil.copytree(root / "zellij/command-prompt", checkout / "zellij/command-prompt",
                        ignore=shutil.ignore_patterns("target"))
        shutil.copyfile(
            root / "scripts/setup-bedrock-credentials.py",
            checkout / "scripts/setup-bedrock-credentials.py",
        )
        token = "test-only-'$(touch \"$HOME/token-executed\")`id`"
        source = home / "user (13).json"
        source.write_text(json.dumps({"bearer_token": token, "region": "us-east-1", "expiration": 4102444800}))
        (checkout / "kitty").mkdir()
        shutil.copyfile(root / "kitty/kitty.terminfo", checkout / "kitty/kitty.terminfo")
        driver = fixture / "driver"
        driver.write_text(f"#!{sys.executable}\n" + r'''
import os
from pathlib import Path
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tomllib
import zipfile

home = Path(os.environ["HOME"])
fixture = home / "fixture"
name = Path(sys.argv[0]).name
args = sys.argv[1:]
managed = str(home / ".local/bin") in sys.argv[0]

def record(event):
    with (home / "events").open("a") as output:
        output.write(event + "\n")

if name == "uname":
    print("Linux" if args == ["-s"] else "aarch64")
elif name == "git":
    if args[:1] == ["-C"] and Path(args[1]).resolve() == (home / ".files").resolve() and args[2:] == ["rev-parse", "--path-format=absolute", "--git-common-dir"]:
        print((home / ".files/.git").resolve())
    elif args[:1] == ["clone"] and "https://github.com/neovim/neovim.git" in args:
        (home / "src/oss/neovim").mkdir(parents=True)
elif name == "sudo":
    if args == ["dnf", "install", "-y", "ImageMagick"]:
        (home / ".local/bin/convert").symlink_to(fixture / "driver")
        record("imagemagick package")
    elif args == ["dnf", "install", "-y", "imagemagick"]:
        sys.exit("No match for argument: imagemagick")
    elif args in (["apt-get", "install", "-y", "tmux"], ["dnf", "install", "-y", "tmux"]):
        (home / ".local/bin/tmux").symlink_to(fixture / "driver")
        record("tmux package")
    elif args in (["apt-get", "install", "-y", "eza"], ["dnf", "install", "-y", "eza"]):
        (home / ".local/bin/eza").symlink_to(fixture / "driver")
        record("eza package")
    else:
        if args[:3] == ["dnf", "install", "-y"] and {"perl-IPC-Cmd", "perl-Time-Piece"}.issubset(args):
            (home / "openssl-perl-installed").touch()
        record("build dependencies")
elif name == "apt-cache":
    assert args[:1] == ["policy"], args
    version = {"eza": "0.20.19-1"}.get(args[1], "(none)")
    print(args[1] + ":\n  Installed: (none)\n  Candidate: " + version)
elif name == "dnf":
    assert args[:2] == ["--cacheonly", "info"], args
    if args[2] != "eza":
        sys.exit(1)
    print("Version : 0.20.19")
elif name == "curl":
    url = next(arg for arg in args if arg.startswith("https://"))
    target = args[args.index("-o" if "-o" in args else "--output") + 1]
    if "uv-installer.sh" in url:
        event = "uv"
        script = 'mkdir -p "$HOME/.local/bin"\nln -fs "$HOME/fixture/driver" "$HOME/.local/bin/uv"\n'
    elif "nvm" in url:
        event = "node"
        script = r"""test "$PROFILE" = /dev/null || exit 1
mkdir -p "$HOME/.nvm"
cat > "$HOME/.nvm/nvm.sh" <<'NVM'
nvm() {
  mkdir -p "$HOME/.nvm/versions/node/v24.0.0/bin" "$HOME/.nvm/alias"
  ln -fs "$HOME/fixture/driver" "$HOME/.nvm/versions/node/v24.0.0/bin/node"
  ln -fs "$HOME/fixture/driver" "$HOME/.nvm/versions/node/v24.0.0/bin/npm"
  echo 24 > "$HOME/.nvm/alias/default"
  export NVM_BIN="$HOME/.nvm/versions/node/v24.0.0/bin"
  export PATH="${PATH/$HOME\/.nvm\/versions\/node\/v16.19.1\/bin/$NVM_BIN}"
}
nvm use
NVM
"""
    elif "rustup" in url:
        event = "rustup"
        script = r"""mkdir -p "$HOME/.cargo/bin"
ln -fs "$HOME/fixture/driver" "$HOME/.cargo/bin/rustup"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' > "$HOME/.cargo/env"
"""
    elif url.startswith("https://github.com/earendil-works/pi/releases/download/v1.4.0/"):
        name = "pi-linux-arm64.tar.gz"
        if url.endswith("/" + name):
            with tarfile.open(target, "w:gz") as archive:
                content = (fixture / "driver").read_bytes()
                binary = tarfile.TarInfo("pi/pi")
                binary.mode = 0o755
                binary.size = len(content)
                archive.addfile(binary, io.BytesIO(content))
            (home / "pi-version").write_text("1.4.0")
            record("pi")
        else:
            assert url.endswith("/SHA256SUMS"), url
            digest = hashlib.sha256(Path(target).with_name(name).read_bytes()).hexdigest()
            Path(target).write_text(f"{digest}  {name}\n")
        sys.exit(0)
    elif url.endswith("/Hack.zip"):
        with zipfile.ZipFile(target, "w") as archive:
            archive.writestr("HackNerdFontMono-Regular.ttf", b"fixture font")
            archive.writestr("HackNerdFont-Regular.ttf", b"non-mono font")
        record("hack font")
        sys.exit(0)
    elif url == "https://claude.ai/install.sh":
        event = "claude"
        script = r"""mkdir -p "$HOME/.local/bin"
ln -fs "$HOME/fixture/driver" "$HOME/.local/bin/claude"
echo "$1" > "$HOME/claude-version"
"""
    elif url == "https://github.com/mikefarah/yq/releases/download/v4.45.4/yq_linux_arm64":
        Path(target).symlink_to(fixture / "driver")
        record("yq")
        sys.exit(0)
    elif url == "https://github.com/aristocratos/btop/releases/download/v1.4.7/btop-aarch64-unknown-linux-musl.tar.gz":
        with tarfile.open(target, "w:gz") as archive:
            for path, payload in (
                ("btop/bin/btop", (fixture / "driver").read_bytes()),
                ("btop/themes/dracula.theme", b"main_bg=\"#000000\"\n"),
            ):
                member = tarfile.TarInfo(path)
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
        record("btop")
        sys.exit(0)
    elif url == "https://github.com/lanej/treehouse/archive/e4c17fdfa6778545c2e073d741e5e837ff19e6c4.tar.gz":
        with tarfile.open(target, "w:gz") as archive:
            payload = b"module github.com/kunchenguid/treehouse/v3\n"
            member = tarfile.TarInfo("treehouse-fork/go.mod")
            member.size = len(payload)
            archive.addfile(member, io.BytesIO(payload))
        sys.exit(0)
    else:
        raise AssertionError("Unexpected download: " + url)
    record(event)
    Path(target).write_text(script)
elif name == "uv":
    if args[:2] == ["python", "install"]:
        record("python")
        destination = home / ".local/bin/python3"
        if not destination.exists():
            destination.symlink_to(fixture / "driver")
    elif args[:3] == ["run", "--no-project", "python"]:
        record("bedrock setup")
        os.execv(sys.executable, [sys.executable, *args[3:]])
    else:
        print("uv 0.12.11" if managed else "uv 0.10.12")
elif name == "python3":
    if args == ["--version"]:
        print("Python 3.12.0" if managed else "Python 3.6.8")
    else:
        # Unknown invocations must execute or fail, rather than silently treating
        # a missing installer script as a successful version query.
        os.execv(sys.executable, [sys.executable, *args])
elif name == "node":
    print("v24.0.0" if ".nvm/versions/" in sys.argv[0] else
          "v22.23.3" if managed else "v16.19.1")
elif name == "bun":
    assert args == ["--version"], args
    print("1.10.0")
elif name == "npm" and args[:1] == ["list"]:
    print('{"dependencies": {"yaml-language-server": {"version": "99.0.0"}}}')
elif name == "npm" and args[:2] == ["install", "-g"]:
    package, version = args[-1].rsplit("@", 1)
    tool = {"@openai/codex": "codex"}[package]
    node_bin = Path(shutil.which("node")).parent
    (node_bin / tool).symlink_to(fixture / "driver")
    (home / (tool + "-version")).write_text(version)
    record(tool)
elif name in ("codex", "claude", "pi"):
    assert args == ["--version"], args
    print(("" if name == "pi" else name + " ") + (home / (name + "-version")).read_text().strip())
elif name == "jq" and args[:1] == ["-r"]:
    print("99.0.0")
elif name in ("eza", "yq"):
    print(name + " " + {"eza": "0.20.19", "yq": "4.45.4"}[name])
elif name == "btop":
    print("btop version: 1.4.7")
elif name == "zellij":
    assert args == ["--version"], args
    print("zellij 0.45.1" if Path(sys.argv[0]).parent == fixture else "zellij 0.46.0")
elif name == "nvim" and args == ["--version"]:
    print("NVIM v0.12.5" if managed else "NVIM v0.11.0")
elif name == "make" and Path.cwd() == (home / "src/oss/neovim").resolve():
    if args[:1] == ["install"]:
        (home / ".local/bin/nvim").symlink_to(fixture / "driver")
        record("neovim build")
    else:
        assert args == ["clean"], args
elif name == "make" and args[-1:] in (["treehouse-config"], ["firstmate-config"]):
    # These integrations configure their already-installed tools before the
    # full environment is ready; the final make below checks all runtimes.
    sys.exit(0)
elif name == "make" and args[-1:] == ["directory-picker"]:
    assert shutil.which("fzf") and shutil.which("go")
    record("directory-picker build")
elif name == "make" and args[-1:] == ["pi-config"]:
    assert subprocess.check_output(["pi", "--version"], text=True).strip() == "1.4.0"
    record("pi config")
elif name == "make" and args[-1:] == ["base"]:
    subprocess.run(["/usr/bin/make", *args], check=True)
    record("base")
elif name == "make" and args[-1:] == ["zellij-helpers"]:
    assert shutil.which("cargo"), "native helpers require Rust"
    record("zellij helpers")
elif name == "make":
    assert {"configure", "atuin-sync", "agent-status-broker", "sql-formatters", "zellij-status", "zellij-config", "zellij-copy-hop"}.intersection(args), args
    for tool in ("node", "python3", "uv", "codex", "claude", "btop", "zellij"):
        value = subprocess.check_output([tool, "--version"], text=True).strip()
        expected = {
            "node": "v24.", "python3": "Python 3.12.", "uv": "uv 0.12.",
            "codex": "codex 0.164.0", "claude": "claude 2.1.295",
            "btop": "btop version: 1.4.7",
            "zellij": "zellij 0.46.0",
        }[tool]
        assert value.startswith(expected), value
    assert shutil.which("rustup"), "rustup missing"
    assert shutil.which("convert"), "ImageMagick missing"
    assert (home / ".local/share/zellij/plugins/pane-navigation.wasm").read_bytes() == b"\0asmfixture"
    assert (home / ".local/share/zellij/plugins/command-prompt.wasm").read_bytes() == b"\0asmfixture"
    assert (home / ".config/bedrock/env").is_file(), "Bedrock credentials missing"
    subprocess.run(
        ["/usr/bin/make", "-f", str(home / ".files/Makefile"), "codex-env"],
        cwd=home / ".files", check=True,
    )
    record("make")
    if "atuin-sync" in args:
        record("atuin setup")
    if "agent-status-broker" in args:
        record("agent status setup")
elif name == "nvim" and "--headless" in args:
    assert (home / ".terminfo/x/xterm-kitty").exists() or (home / ".terminfo/78/xterm-kitty").exists()
    assert "make" in (home / "events").read_text()
    assert os.environ["DOTFILES_NVIM_BOOTSTRAP"].endswith("/scripts/bootstrap-nvim.lua")
    record("neovim setup")
elif name == "loginctl":
    print("Linger=yes")
elif name == "git-crypt":
    if args != ["version"]:
        sys.exit(2)
    print("git-crypt 0.8.0")
elif name == "rustup" and args[:3] == ["run", "1.95.0", "rustc"]:
    assert args[3:] == ["-vV"], args
    print("rustc 1.95.0\nhost: aarch64-unknown-linux-gnu\n")
elif name == "rustup" and args[:4] == ["run", "1.95.0", "cargo", "build"]:
    assert "--locked" in args and args[args.index("--target") + 1] == "wasm32-wasip1", args
    manifest = Path(args[args.index("--manifest-path") + 1])
    package = tomllib.loads(manifest.read_text())["package"]["name"]
    assert package in ("dotfiles-pane-navigation", "dotfiles-command-prompt"), package
    output = Path(os.environ["CARGO_TARGET_DIR"]) / "wasm32-wasip1/release" / (package + ".wasm")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"\0asmfixture")
elif name == "rustup" and args[:3] == ["run", "1.95.0", "cargo"]:
    assert args[3] == "install", args
    if args[4:] == ["--list", "--root", str(home / ".local")]:
        if (home / "zellij-owned").exists():
            print("zellij v0.46.0:\n    zellij")
        sys.exit(0)
    assert (home / "openssl-perl-installed").exists(), "vendored OpenSSL needs IPC::Cmd and Time::Piece"
    assert args[args.index("--git") + 1] == "https://github.com/lanej/zellij.git", args
    revision = args[args.index("--rev") + 1]
    assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision), args
    assert "--locked" in args and "--no-default-features" in args, args
    assert args[args.index("--features") + 1] == "plugins_from_target,vendored_curl,web_server_capability", args
    assert args[-3:] == ["--bin", "zellij", "zellij"], args
    assert os.environ["CARGO_PROFILE_RELEASE_LTO"] == "true"
    assert os.environ["CARGO_PROFILE_RELEASE_CODEGEN_UNITS"] == "1"
    target = args[args.index("--target") + 1]
    assert target == "aarch64-unknown-linux-gnu", args
    install_root = Path(args[args.index("--root") + 1])
    assert install_root == home / ".local", args
    with (home / "zellij-installs").open("a") as installs:
        installs.write(json.dumps({"revision": revision,
                                  "target_dir": os.environ["CARGO_TARGET_DIR"],
                                  "force": "--force" in args}) + "\n")
    if os.environ.get("FIXTURE_FAIL_ZELLIJ_INSTALL"):
        sys.exit("fixture native build failed")
    output = install_root / "bin/zellij"
    if output.exists() and "--force" not in args:
        if (home / "zellij-owned").exists():
            if (home / "zellij-owned").read_text() == revision:
                sys.exit(0)
        else:
            sys.exit("zellij already exists; use --force to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture / "driver", output)
    output.chmod(0o755)
    (home / "zellij-owned").write_text(revision)
    record("zellij")
elif name == "cargo" and args[:2] == ["install", "mergiraf"]:
    assert args == ["install", "mergiraf", "-q", "--locked", "--version", "0.20.0"], args
    (home / ".cargo/bin/mergiraf").symlink_to(fixture / "driver")
    record("mergiraf")
elif name == "mergiraf":
    assert args == ["--version"], args
    print("mergiraf 0.20.0")
elif name in ("cargo", "rustc", "rustup", "rust-analyzer"):
    print(name + " 1.93.1")
elif name == "go":
    if args[:1] == ["build"]:
        assert os.environ["CGO_ENABLED"] == "0"
        assert args[args.index("-ldflags") + 1] == "-X main.version=dev", args
        assert os.environ["GOOS"] == "linux" and os.environ["GOARCH"] == "arm64"
        assert Path("go.mod").is_file()
        output = Path(args[args.index("-o") + 1])
        shutil.copyfile(fixture / "driver", output)
        output.chmod(0o755)
        record("treehouse build")
    elif args == ["env", "GOHOSTOS"]:
        print("linux")
    elif args == ["env", "GOHOSTARCH"]:
        print("arm64")
    elif args == ["env", "GOBIN"]:
        print("")
    elif args == ["env", "GOPATH"]:
        print(os.environ["GOPATH"])
    elif args[:1] == ["install"]:
        assert "charmbracelet/glow" in args[1], args
        destination = Path(os.environ["GOPATH"]) / "bin"
        destination.mkdir(parents=True)
        (destination / "glow").symlink_to(fixture / "driver")
    elif args[:2] == ["version", "-m"]:
        assert args[2].endswith("/glow"), args
        print("\tmod\tgithub.com/charmbracelet/glow/v2\tv2.0.0\tfixture")
    else:
        print("go version go1.26.2 linux/amd64")
elif name == "glow":
    print("glow version master")
elif name == "treehouse":
    print("dev")
elif name == "gh" and args == ["auth", "status"]:
    sys.exit(1)
else:
    print(name + " 99.0.0")
''')
        driver.chmod(0o755)
        suggestions = home / ".zsh/plugins/zsh-autosuggestions"
        suggestions.mkdir(parents=True)
        (suggestions / "zsh-autosuggestions.zsh").write_text("# version 99.0.0\n")
        for tool in (
            "uname", "git", "sudo", "apt-get", "apt-cache", "dnf", "curl", "uv", "node", "npm", "bun",
            "make", "cmake", "cc", "cargo", "rustc", "rust-analyzer", "go",
            "fzf", "starship", "atuin", "sk", "delta", "bat", "fd",
            "zsh-autosuggestions", "cargo-sweep", "cargo-cache",
            "gh", "git-crypt", "jq", "rg", "stylua", "nvim", "shfmt",
            "bash-language-server", "typescript-language-server", "gopls",
            "gotestsum", "ctags-lsp", "tree-sitter", "hexyl", "yaml-language-server",
            "direnv", "just", "loginctl", "zellij", "lsof",
            "no-mistakes", "gh-axi", "tasks-axi", "quota-axi",
            "chrome-devtools-axi", "lavish-axi",
        ):
            (fixture / tool).symlink_to(driver)
        # Keep this fresh-box workflow independent of tools preinstalled on CI.
        system_bin = home / "system-bin"
        system_bin.mkdir()
        missing_tools = {"python3", "tmux", "eza", "yq", "btop", "pi", "zellij", "rustup", "convert", "magick", "imagemagick", "treehouse"}
        for system_dir in (Path("/usr/bin"), Path("/bin")):
            for tool in system_dir.iterdir():
                destination = system_bin / tool.name
                if (tool.name not in missing_tools and tool.is_file()
                        and os.access(tool, os.X_OK) and not destination.is_symlink()):
                    destination.symlink_to(tool)
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fixture}:{system_bin}",
            "ATUIN_SYNC_HOST": "fixture-host",
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "CARGO_BUILD_TARGET": "x86_64-unknown-linux-gnu",
        }
        env.pop("GOPATH", None)
        env.pop("GOBIN", None)
        env.pop("DOTFILES_CONFIG", None)
        env.pop("IS_EASYPOST", None)
        env.pop("BOOTSTRAP_MERMAID", None)
        # Stage one provides the native baseline and configuration runtime,
        # without installing the selected workstation or work integrations.
        result = subprocess.run(
            ["/bin/bash", "./bootstrap.sh"],
            cwd=checkout, env=env, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        assert (home / ".xinitrc").is_symlink()
        assert (home / ".gitconfig").resolve() == (checkout / "git/gitconfig").resolve()
        assert (home / ".local/bin/uv").is_file()
        assert (home / ".local/bin/python3").is_file()
        assert not (home / "patched-git-installed").exists()
        assert not (home / "studio-installed").exists()
        assert not (home / ".nvm").exists()
        assert not (home / ".cargo").exists()
        assert not (home / ".local/bin/codex").exists()
        assert not (home / ".config/bedrock/env").exists()

        # An up-to-date npm launcher must not satisfy the standalone Pi install.
        legacy_pi = fixture / "pi"
        legacy_pi.symlink_to(driver)
        (home / "pi-version").write_text("1.4.0")

        # Stage two installs the configured workstation on ARM Linux, including
        # an older Neovim that needs a source build and missing eza/yq/btop.
        machine_config.write_text('sets = ["workstation", "easypost"]\n[tools]\nmermaid = false\npi = true\nworktree-manager = true\nworktree-policy = true\ntreehouse = true\n')
        plan = subprocess.run(
            ["/usr/bin/make", "--no-print-directory", "plan"],
            cwd=checkout, env=env, capture_output=True, text=True,
        )
        assert plan.returncode == 0, plan.stdout + plan.stderr
        assert "codex" in {tool["name"] for tool in json.loads(plan.stdout)["tools"]}
        assert "git-worktree-hooks" in {tool["name"] for tool in json.loads(plan.stdout)["tools"]}
        preview = subprocess.run(
            ["/usr/bin/make", "--no-print-directory", "-n", "configure"],
            cwd=checkout, env=env, capture_output=True, text=True,
        )
        assert preview.returncode == 0, preview.stdout + preview.stderr
        # WHY: NVM replaces an inherited NVM entry in place, so another Node
        # executable earlier in PATH can still shadow the selected version.
        shadow_node = home / ".local/bin/node"
        shadow_node.symlink_to(driver)
        env["PATH"] = f"{fixture}:{home}/.nvm/versions/node/v16.19.1/bin:{system_bin}"
        result = subprocess.run(
            ["/usr/bin/make", "--no-print-directory", "install"],
            cwd=checkout, env=env, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        assert shadow_node.is_symlink() and shadow_node.resolve() == driver.resolve()
        events = (home / "events").read_text().splitlines()
        assert legacy_pi.resolve() == driver.resolve()
        assert (home / ".local/bin/pi").readlink() == home / ".local/share/pi-standalone/1.4.0/pi/pi"
        assert "mergiraf" in events
        assert (home / ".cargo/bin/mergiraf").is_file()
        assert events.index("make") > max(
            events.index(tool) for tool in ("uv", "node", "python", "rustup", "codex", "claude", "pi")
        )
        assert "neovim setup" in events
        assert "neovim build" in events
        assert "eza package" in events
        assert "treehouse build" in events
        assert "directory-picker build" in events
        treehouse_command = ["/bin/bash", str(checkout / "scripts/install-treehouse")]
        for replaced in (False, True):
            if replaced:
                (home / ".local/bin/treehouse").write_text('#!/bin/sh\necho v99.0.0\n')
            repeated = subprocess.run(treehouse_command, env=env, capture_output=True, text=True)
            assert repeated.returncode == 0, repeated.stdout + repeated.stderr
            assert (home / "events").read_text().splitlines().count("treehouse build") == (2 if replaced else 1)
        assert (home / ".local/bin/tmux").is_file()
        assert events.index("tmux package") < events.index("make")
        assert "yq" in events
        assert "btop" in events
        assert (home / ".local/bin/zellij").is_file()
        assert "zellij helpers" in (home / "events").read_text()
        assert events.index("zellij") < events.index("make")
        # Repeat the real entrypoint with the installed executable already in
        # place. Cargo owns installation and caching; the fixture models its output.
        runtime_command = ["/bin/bash", str(checkout / "scripts/install-zellij")]
        runtime_env = {**env, "PATH": f"{home / '.cargo/bin'}:{env['PATH']}",
                       "CARGO_PROFILE_RELEASE_LTO": "false",
                       "CARGO_PROFILE_RELEASE_CODEGEN_UNITS": "16"}
        installed = home / ".local/bin/zellij"
        previous = installed.read_bytes()
        repeated = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert installed.read_bytes() == previous
        assert (home / "events").read_text().splitlines().count("zellij") == 1
        # Model a legacy owned same-revision installation without a receipt.
        # Keep its populated build cache: cache state cannot verify the binary.
        def runtime_calls():
            return [json.loads(line) for line in (home / "zellij-installs").read_text().splitlines()]

        first_call, repeat_call = runtime_calls()
        revision = first_call["revision"]
        assert first_call["target_dir"] == str(home / ".cache/dotfiles/zellij/target" / revision)
        assert first_call["force"] and not repeat_call["force"]
        (home / ".local/.dotfiles-zellij-install").unlink(missing_ok=True)
        failed = subprocess.run(runtime_command,
                                env={**runtime_env, "FIXTURE_FAIL_ZELLIJ_INSTALL": "1"},
                                capture_output=True, text=True)
        assert failed.returncode != 0 and "fixture native build failed" in failed.stderr
        assert installed.read_bytes() == previous
        migrated = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert migrated.returncode == 0, migrated.stdout + migrated.stderr
        assert runtime_calls()[-1]["force"], "A failed build was treated as an installed isolated runtime"
        assert (home / "events").read_text().splitlines().count("zellij") == 2
        repeated = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert not runtime_calls()[-1]["force"]
        assert (home / "events").read_text().splitlines().count("zellij") == 2
        receipt = home / ".local/.dotfiles-zellij-install"
        receipt.write_text(f"revision-target-v1:{revision}\n")
        failed = subprocess.run(runtime_command,
                                env={**runtime_env, "FIXTURE_FAIL_ZELLIJ_INSTALL": "1"},
                                capture_output=True, text=True)
        assert failed.returncode != 0 and runtime_calls()[-1]["force"]
        assert installed.read_bytes() == previous
        assert receipt.read_text() == f"revision-target-v1:{revision}\n"
        optimized = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert optimized.returncode == 0, optimized.stdout + optimized.stderr
        assert runtime_calls()[-1]["force"], "Old-profile installation skipped the optimized rebuild"
        repeated = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert not runtime_calls()[-1]["force"], "Matching optimized installation rebuilt unnecessarily"
        isolated_target = runtime_calls()[-1]["target_dir"]
        # Exercise a second pinned recipe through the same installer entrypoint.
        alternate_revision = "1" * 40
        alternate = home / "install-zellij-other"
        alternate.write_text((checkout / "scripts/install-zellij").read_text().replace(
            "zellij_revision=" + revision, "zellij_revision=" + alternate_revision))
        changed = subprocess.run(["/bin/bash", str(alternate)], env=runtime_env,
                                 capture_output=True, text=True)
        assert changed.returncode == 0, changed.stdout + changed.stderr
        changed_call = runtime_calls()[-1]
        assert changed_call["revision"] == alternate_revision
        assert changed_call["target_dir"] != isolated_target and changed_call["force"]
        assert Path(changed_call["target_dir"]).name == alternate_revision
        restored = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert restored.returncode == 0, restored.stdout + restored.stderr
        assert runtime_calls()[-1]["target_dir"] == isolated_target
        assert runtime_calls()[-1]["force"], "Returning to an old pin trusted build-cache state"
        assert (home / "zellij-owned").read_text() == revision
        font_dir = home / ".local/share/fonts"
        assert (font_dir / "HackNerdFontMono-Regular.ttf").read_bytes() == b"fixture font"
        assert not (font_dir / "HackNerdFont-Regular.ttf").exists()
        font_rerun = subprocess.run(
            ["bash", "-ec", 'source "$1"; install_hack_nerd_font', "bash", str(checkout / "bootstrap.sh")],
            env=env, capture_output=True, text=True,
        )
        assert font_rerun.returncode == 0, font_rerun.stdout + font_rerun.stderr
        assert (home / "events").read_text().splitlines().count("hack font") == 1
        assert (home / ".local/share/btop/themes/dracula.theme").is_file()
        assert "atuin setup" in events
        assert router_binary.read_bytes() == b"externally installed router"
        assert router_config.read_bytes() == b"external router configuration"
        assert router_state.read_bytes() == b"external session database"
        assert events.index("agent status setup") > events.index("make")
        assert (home / ".codex/.env").resolve() == (home / ".config/bedrock/env").resolve()
        credential_file = home / ".config/bedrock/env"
        assert events.index("bedrock setup") < events.index("make")
        assert credential_file.stat().st_mode & 0o777 == 0o600
        assert source.stat().st_mode & 0o777 == 0o600
        loaded = subprocess.run(
            ["/bin/bash", "-c", 'source "$1"; test "$AWS_BEARER_TOKEN_BEDROCK" = "$2" && test "$AWS_REGION" = us-east-1',
             "bedrock-test", str(credential_file), token],
            env=env, capture_output=True, text=True,
        )
        assert loaded.returncode == 0, "Bedrock credentials did not survive shell quoting."
        assert not (home / "token-executed").exists(), "Token executed shell code."
        assert token not in result.stdout + result.stderr
        # A rerun preserves credentials even if the original export changes.
        previous = credential_file.read_bytes()
        source.write_text(json.dumps({"bearer_token": "changed-test-only", "region": "us-west-2"}))
        rerun = subprocess.run(
            [sys.executable, str(checkout / "scripts/setup-bedrock-credentials.py")],
            env=env, capture_output=True, text=True,
        )
        assert rerun.returncode == 0 and credential_file.read_bytes() == previous
        selected = home / "token '$(touch selected-token-executed).json"
        selected.write_text(json.dumps({"bearer_token": "selected-test-only", "region": "us-west-2"}))
        selected_install = subprocess.run(
            ["/usr/bin/make", "-f", str(root / "Makefile"), "bedrock-credentials"],
            cwd=checkout,
            env={**env, "BEDROCK_TOKEN_FILE": str(selected)},
            capture_output=True, text=True,
        )
        assert selected_install.returncode == 0, selected_install.stdout + selected_install.stderr
        selected_loaded = subprocess.run(
            ["/bin/bash", "-c", 'source "$1"; test "$AWS_BEARER_TOKEN_BEDROCK" = selected-test-only && test "$AWS_REGION" = us-west-2',
             "bedrock-test", str(credential_file)],
            env=env, capture_output=True, text=True,
        )
        assert selected_loaded.returncode == 0, "Explicitly selected credentials were not installed."
        assert not (checkout / "selected-token-executed").exists()
        assert "Dotfiles installation completed!" in result.stdout

        # A local property removes the editor from the same composed bundles.
        # Keep an older system editor present: installation must leave it alone
        # and skip both the source install and Neovim's post-install setup.
        machine_config.write_text(machine_config.read_text() + "neovim = false\nstudio = false\n")
        (home / ".local/bin/nvim").unlink()
        (home / "pi-version").write_text("1.5.0")
        previous_events = len((home / "events").read_text().splitlines())
        reduced = subprocess.run(["/bin/bash", "./bootstrap.sh", "install"], cwd=checkout, env=env,
                                 capture_output=True, text=True)
        assert reduced.returncode == 0, reduced.stdout + reduced.stderr
        new_events = (home / "events").read_text().splitlines()[previous_events:]
        assert "neovim build" not in new_events and "neovim setup" not in new_events
        assert "studio install" not in new_events
        assert "pi" not in new_events
        assert "mergiraf" not in new_events
        assert (home / "pi-version").read_text() == "1.5.0"
        assert "node" not in new_events and "zellij" not in new_events
        assert not (home / ".local/bin/nvim").exists()
        assert (home / "patched-git-installed").is_file()
        assert (home / "native-policy-installed").is_file()
        assert (home / "intent-installed").is_file()
        assert (home / "studio-installed").is_file()
        assert (home / "keylease-installed").is_file()
        assert (home / "worktree-manager-installed").is_file()
        print("PASS: minimal bootstrap provides the native baseline and runtime; explicit installation adds selected tools and private Bedrock credentials.")


if __name__ == "__main__":
    main()
