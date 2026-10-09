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
        checkout = home / ".files"
        checkout.mkdir()
        shutil.copyfile(root / "bootstrap.sh", checkout / "bootstrap.sh")
        shutil.copyfile(root / "Makefile", checkout / "Makefile")
        (checkout / "scripts").mkdir()
        shutil.copyfile(
            root / "scripts/setup-bedrock-credentials.py",
            checkout / "scripts/setup-bedrock-credentials.py",
        )
        token = "test-only-'$(touch \"$HOME/token-executed\")`id`"
        source = home / "user (13).json"
        source.write_text(json.dumps({"bearer_token": token, "region": "us-east-1", "expiration": 4102444800}))
        (checkout / "kitty").mkdir()
        shutil.copyfile(root / "kitty/kitty.terminfo", checkout / "kitty/kitty.terminfo")
        (checkout / "codex/bedrock-router").mkdir(parents=True)
        driver = fixture / "driver"
        driver.write_text(f"#!{sys.executable}\n" + r'''
import os
from pathlib import Path
import io
import shutil
import subprocess
import sys
import tarfile

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
    if args == ["apt-get", "install", "-y", "eza"]:
        (home / ".local/bin/eza").symlink_to(fixture / "driver")
        record("apt eza")
    else:
        record("build dependencies")
elif name == "apt-cache":
    assert args[:1] == ["policy"], args
    version = {"eza": "0.20.19-1"}.get(args[1], "(none)")
    print(args[1] + ":\n  Installed: (none)\n  Candidate: " + version)
elif name == "curl":
    url = next(arg for arg in args if arg.startswith("https://"))
    target = args[args.index("-o") + 1]
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
    else:
        raise AssertionError("Unexpected download: " + url)
    record(event)
    Path(target).write_text(script)
elif name == "uv":
    if args[:2] == ["python", "install"]:
        record("python")
        (home / ".local/bin/python3").symlink_to(fixture / "driver")
    elif args[:3] == ["run", "--no-project", "python"]:
        record("bedrock setup")
        os.execv(sys.executable, [sys.executable, *args[3:]])
    else:
        print("uv 0.12.11" if managed else "uv 0.10.12")
elif name == "python3":
    print("Python 3.12.0" if managed else "Python 3.6.8")
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
elif name == "nvim" and args == ["--version"]:
    print("NVIM v0.12.5" if managed else "NVIM v0.11.0")
elif name == "make" and Path.cwd() == (home / "src/oss/neovim").resolve():
    if args[:1] == ["install"]:
        (home / ".local/bin/nvim").symlink_to(fixture / "driver")
        record("neovim build")
    else:
        assert args == ["clean"], args
elif name == "make":
    for tool in ("node", "python3", "uv", "codex", "claude", "btop"):
        value = subprocess.check_output([tool, "--version"], text=True).strip()
        expected = {
            "node": "v24.", "python3": "Python 3.12.", "uv": "uv 0.12.",
            "codex": "codex 0.162.0", "claude": "claude 2.1.295",
            "btop": "btop version: 1.4.7",
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
elif name == "nvim" and "--headless" in args:
    assert (home / ".terminfo/x/xterm-kitty").exists() or (home / ".terminfo/78/xterm-kitty").exists()
    assert "make" in (home / "events").read_text()
    assert os.environ["DOTFILES_NVIM_BOOTSTRAP"].endswith("/scripts/bootstrap-nvim.lua")
    record("neovim setup")
elif name == "bedrock-router":
    assert args[:2] == ["install", "--config"] and args[3:] == ["--keep-env"], args
    assert Path(args[2]).resolve() == (home / ".files/codex/bedrock-router/config.json").resolve()
    assert "make" in (home / "events").read_text()
    assert (home / ".config/bedrock/env").stat().st_mode & 0o777 == 0o600
    record("router setup")
elif name == "loginctl":
    print("Linger=yes")
elif name == "cargo" and args[:1] == ["install"]:
    assert "ssh://git@github.com/easypost-sandbox/kagi.git" in args, args
    (home / ".cargo/bin/kagi").symlink_to(fixture / "driver")
    (home / ".cargo/.crates.toml").write_text('"kagi 0.1.0 (git+ssh://fixture)" = ["kagi"]\n')
elif name == "kagi":
    sys.exit(2)  # The actual CLI does not support --version.
elif name == "git-crypt":
    if args != ["version"]:
        sys.exit(2)
    print("git-crypt 0.8.0")
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
    elif args[:1] == ["build"]:
        assert Path.cwd() == (home / ".files/codex/bedrock-router").resolve()
        Path(args[args.index("-o") + 1]).symlink_to(fixture / "driver")
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
            "uname", "git", "sudo", "apt-get", "apt-cache", "curl", "uv", "node", "npm",
            "python3", "make", "cargo", "rustc", "rust-analyzer", "go",
            "fzf", "starship", "atuin", "sk", "delta", "bat", "fd",
            "zsh-autosuggestions", "cargo-sweep", "cargo-cache",
            "gh", "git-crypt", "jq", "rg", "stylua", "nvim", "shfmt",
            "bash-language-server", "typescript-language-server", "gopls",
            "gotestsum", "ctags-lsp", "tree-sitter", "hexyl", "yaml-language-server",
            "direnv", "just", "loginctl",
        ):
            (fixture / tool).symlink_to(driver)
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fixture}:/usr/bin:/bin",
        }
        env.pop("GOPATH", None)
        env.pop("GOBIN", None)
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
        assert "apt eza" in events
        assert "yq" in events
        assert "btop" in events
        assert (home / ".local/share/btop/themes/dracula.theme").is_file()
        assert "atuin setup" in events
        assert events.index("router setup") > events.index("make")
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
        print("PASS: fresh-box bootstrap installs runtimes, AI CLIs, and private Bedrock credentials.")


if __name__ == "__main__":
    main()
