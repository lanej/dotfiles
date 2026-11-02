#!/usr/bin/env python3
"""One fresh-box bootstrap workflow; downloads and package managers are fixtures."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="dotfiles-bootstrap-") as temporary:
        home = Path(temporary)
        fixture = home / "fixture"
        fixture.mkdir()
        # Model the unmanaged executable left by the previous runtime installer.
        installed = home / ".local/bin/zellij"
        installed.parent.mkdir(parents=True)
        installed.write_text('#!/bin/sh\necho "zellij 0.45.1"\n')
        installed.chmod(0o755)
        checkout = home / ".files"
        checkout.mkdir()
        shutil.copyfile(root / "bootstrap.sh", checkout / "bootstrap.sh")
        shutil.copyfile(root / "Makefile", checkout / "Makefile")
        shutil.copytree(root / "config", checkout / "config")
        shutil.copytree(root / "bootstrap", checkout / "bootstrap")
        (checkout / "scripts").mkdir()
        shutil.copyfile(root / "scripts/dotfiles-config.py", checkout / "scripts/dotfiles-config.py")
        machine_config = home / ".config/dotfiles/config.toml"
        machine_config.parent.mkdir(parents=True)
        machine_config.write_text('sets = ["workstation", "easypost"]\n[tools]\nmermaid = false\n')
        shutil.copytree(root / "scripts/make", checkout / "scripts/make")
        shutil.copyfile(root / "scripts/install-zellij", checkout / "scripts/install-zellij")
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
import io
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
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
    if args[:1] == ["clone"] and "https://github.com/neovim/neovim.git" in args:
        (home / "src/oss/neovim").mkdir(parents=True)
elif name == "sudo":
    if args in (["apt-get", "install", "-y", "tmux"], ["dnf", "install", "-y", "tmux"]):
        (home / ".local/bin/tmux").symlink_to(fixture / "driver")
        record("tmux package")
    elif args in (["apt-get", "install", "-y", "eza"], ["dnf", "install", "-y", "eza"]):
        (home / ".local/bin/eza").symlink_to(fixture / "driver")
        record("eza package")
    else:
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
  export PATH="$HOME/.nvm/versions/node/v24.0.0/bin:$PATH"
}
NVM
"""
    elif "rustup" in url:
        event = "rustup"
        script = r"""mkdir -p "$HOME/.cargo/bin"
ln -fs "$HOME/fixture/driver" "$HOME/.cargo/bin/rustup"
echo 'export PATH="$HOME/.cargo/bin:$PATH"' > "$HOME/.cargo/env"
"""
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
    elif url.endswith("/bedrock-router_v0.1.1_linux_arm64.tar.gz"):
        assert url.startswith("https://github.com/lanej/bedrock-router/releases/download/v0.1.1/")
        with tarfile.open(target, "w:gz") as archive:
            for path, payload in (
                ("bedrock-router", (fixture / "driver").read_bytes()),
                ("config.json", b'{"fixture": "standalone-router"}\n'),
            ):
                member = tarfile.TarInfo(path)
                member.size = len(payload)
                member.mode = 0o755 if path == "bedrock-router" else 0o644
                archive.addfile(member, io.BytesIO(payload))
        record("router release")
        sys.exit(0)
    elif url == "https://github.com/lanej/bedrock-router/releases/download/v0.1.1/SHA256SUMS":
        release_archive = Path(target).with_name("bedrock-router_v0.1.1_linux_arm64.tar.gz")
        digest = hashlib.sha256(release_archive.read_bytes()).hexdigest()
        Path(target).write_text(digest + "  " + release_archive.name + "\n")
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
    print("v24.0.0" if ".nvm/versions/" in sys.argv[0] else "v16.19.1")
elif name == "npm" and args[:1] == ["list"]:
    print('{"dependencies": {"yaml-language-server": {"version": "99.0.0"}}}')
elif name == "npm" and args[:2] == ["install", "-g"]:
    package, version = args[2].rsplit("@", 1)
    assert package == "@openai/codex", args
    node_bin = Path(shutil.which("node")).parent
    (node_bin / "codex").symlink_to(fixture / "driver")
    (home / "codex-version").write_text(version)
    record("codex")
elif name in ("codex", "claude"):
    assert args == ["--version"], args
    print(name + " " + (home / (name + "-version")).read_text().strip())
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
elif name == "make":
    assert {"configure", "atuin-sync", "agent-status-broker", "sql-formatters"}.intersection(args), args
    for tool in ("node", "python3", "uv", "codex", "claude", "btop", "zellij"):
        value = subprocess.check_output([tool, "--version"], text=True).strip()
        expected = {
            "node": "v24.", "python3": "Python 3.12.", "uv": "uv 0.12.",
            "codex": "codex 0.162.0", "claude": "claude 2.1.295",
            "btop": "btop version: 1.4.7",
            "zellij": "zellij 0.46.0",
        }[tool]
        assert value.startswith(expected), value
    assert shutil.which("rustup"), "rustup missing"
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
elif name == "bedrock-router":
    assert args[:2] == ["install", "--config"] and args[3:] == ["--keep-env"], args
    assert json.loads(Path(args[2]).read_text()) == {"fixture": "standalone-router"}
    assert "make" in (home / "events").read_text()
    assert (home / ".config/bedrock/env").stat().st_mode & 0o777 == 0o600
    record("router setup")
elif name == "loginctl":
    print("Linger=yes")
elif name == "git-crypt":
    if args != ["version"]:
        sys.exit(2)
    print("git-crypt 0.8.0")
elif name == "rustup" and args[:3] == ["run", "1.95.0", "rustc"]:
    assert args[3:] == ["-vV"], args
    print("rustc 1.95.0\nhost: aarch64-unknown-linux-gnu\n")
elif name == "rustup" and args[:3] == ["run", "1.95.0", "cargo"]:
    assert args[3] == "install", args
    assert args[args.index("--git") + 1] == "https://github.com/lanej/zellij.git", args
    revision = args[args.index("--rev") + 1]
    assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision), args
    assert "--locked" in args and "--no-default-features" in args, args
    assert args[args.index("--features") + 1] == "plugins_from_target,vendored_curl,web_server_capability", args
    assert args[-3:] == ["--bin", "zellij", "zellij"], args
    target = args[args.index("--target") + 1]
    assert target == "aarch64-unknown-linux-gnu", args
    install_root = Path(args[args.index("--root") + 1])
    assert install_root == home / ".local", args
    output = install_root / "bin/zellij"
    if output.exists() and "--force" not in args:
        sys.exit("zellij already exists; use --force to overwrite")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(fixture / "driver", output)
    output.chmod(0o755)
    record("zellij")
elif name in ("cargo", "rustc", "rustup", "rust-analyzer"):
    print(name + " 1.93.1")
elif name == "go":
    if args == ["env", "GOBIN"]:
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
            "uname", "git", "sudo", "apt-get", "apt-cache", "dnf", "curl", "uv", "node", "npm",
            "python3", "make", "cmake", "cc", "cargo", "rustc", "rust-analyzer", "go",
            "fzf", "starship", "atuin", "sk", "delta", "bat", "fd",
            "zsh-autosuggestions", "cargo-sweep", "cargo-cache",
            "gh", "git-crypt", "jq", "rg", "stylua", "nvim", "shfmt",
            "bash-language-server", "typescript-language-server", "gopls",
            "gotestsum", "ctags-lsp", "tree-sitter", "hexyl", "yaml-language-server",
            "direnv", "just", "loginctl", "zellij",
            "treehouse", "no-mistakes", "gh-axi", "tasks-axi", "quota-axi",
            "chrome-devtools-axi", "lavish-axi",
        ):
            (fixture / tool).symlink_to(driver)
        # Keep this fresh-box workflow independent of tools preinstalled on CI.
        system_bin = home / "system-bin"
        system_bin.mkdir()
        missing_tools = {"tmux", "eza", "yq", "btop", "rustup"}
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
            "CARGO_BUILD_TARGET": "x86_64-unknown-linux-gnu",
        }
        env.pop("GOPATH", None)
        env.pop("GOBIN", None)
        env.pop("DOTFILES_CONFIG", None)
        env.pop("IS_EASYPOST", None)
        env.pop("BOOTSTRAP_MERMAID", None)
        # Exercise the documented relative launch on ARM Linux, including an
        # older Neovim that needs a source build and missing eza/yq/btop.
        result = subprocess.run(
            ["/bin/bash", "./bootstrap.sh"],
            cwd=checkout, env=env, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        events = (home / "events").read_text().splitlines()
        assert events.index("make") > max(
            events.index(tool) for tool in ("uv", "node", "python", "rustup", "codex", "claude")
        )
        assert "neovim setup" in events
        assert "neovim build" in events
        assert "eza package" in events
        assert (home / ".local/bin/tmux").is_file()
        assert events.index("tmux package") < events.index("make")
        assert "yq" in events
        assert "btop" in events
        assert (home / ".local/bin/zellij").is_file()
        assert events.index("zellij") < events.index("make")
        # Repeat the real entrypoint with the installed executable already in
        # place. Cargo owns installation and caching; the fixture models its output.
        runtime_command = ["/bin/bash", str(checkout / "scripts/install-zellij")]
        runtime_env = {**env, "PATH": f"{home / '.cargo/bin'}:{env['PATH']}"}
        previous = installed.read_bytes()
        repeated = subprocess.run(runtime_command, env=runtime_env, capture_output=True, text=True)
        assert repeated.returncode == 0, repeated.stdout + repeated.stderr
        assert installed.read_bytes() == previous
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
        assert events.index("router setup") > events.index("make")
        assert events.index("router release") < events.index("router setup")
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
        assert "Bootstrap installation completed!" in result.stdout

        # A local property removes the editor from the same composed bundles.
        # Keep an older system editor present: bootstrap must leave it alone
        # and skip both the source install and Neovim's post-install setup.
        machine_config.write_text(machine_config.read_text() + "neovim = false\n")
        (home / ".local/bin/nvim").unlink()
        previous_events = len((home / "events").read_text().splitlines())
        reduced = subprocess.run(["/bin/bash", "./bootstrap.sh"], cwd=checkout, env=env,
                                 capture_output=True, text=True)
        assert reduced.returncode == 0, reduced.stdout + reduced.stderr
        new_events = (home / "events").read_text().splitlines()[previous_events:]
        assert "neovim build" not in new_events and "neovim setup" not in new_events
        assert not (home / ".local/bin/nvim").exists()
        print("PASS: fresh-box bootstrap installs runtimes, AI CLIs, and private Bedrock credentials.")


if __name__ == "__main__":
    main()
