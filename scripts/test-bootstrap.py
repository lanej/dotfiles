#!/usr/bin/env python3
"""One fresh-box bootstrap workflow; downloads and package managers are fixtures."""
from pathlib import Path
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
        (checkout / "kitty").mkdir()
        shutil.copyfile(root / "kitty/kitty.terminfo", checkout / "kitty/kitty.terminfo")
        driver = fixture / "driver"
        driver.write_text(f"#!{sys.executable}\n" + r'''
import os
from pathlib import Path
import shutil
import subprocess
import sys

home = Path(os.environ["HOME"])
fixture = home / "fixture"
name = Path(sys.argv[0]).name
args = sys.argv[1:]
managed = str(home / ".local/bin") in sys.argv[0]

def record(event):
    with (home / "events").open("a") as output:
        output.write(event + "\n")

if name == "uname":
    print("Linux" if args == ["-s"] else "x86_64")
elif name == "git":
    pass
elif name == "sudo":
    record("build dependencies")
elif name == "dnf":
    sys.exit(1)  # Cached distro packages cannot supply the requested versions.
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
    else:
        raise AssertionError("Unexpected download: " + url)
    record(event)
    Path(target).write_text(script)
elif name == "uv":
    if args[:2] == ["python", "install"]:
        record("python")
        (home / ".local/bin/python3").symlink_to(fixture / "driver")
    else:
        print("uv 0.12.11" if managed else "uv 0.10.12")
elif name == "python3":
    print("Python 3.12.0" if managed else "Python 3.6.8")
elif name == "node":
    print("v24.0.0" if ".nvm/versions/" in sys.argv[0] else "v16.19.1")
elif name == "npm" and args[:1] == ["list"]:
    print('{"dependencies": {"yaml-language-server": {"version": "99.0.0"}}}')
elif name == "jq" and args[:1] == ["-r"]:
    print("99.0.0")
elif name == "make":
    for tool in ("node", "python3", "uv"):
        value = subprocess.check_output([tool, "--version"], text=True).strip()
        expected = {"node": "v24.", "python3": "Python 3.12.", "uv": "uv 0.12."}[tool]
        assert value.startswith(expected), value
    assert shutil.which("rustup"), "rustup missing"
    record("make")
    if "atuin-sync" in args:
        record("atuin setup")
elif name == "nvim" and "--headless" in args:
    assert (home / ".terminfo/x/xterm-kitty").exists() or (home / ".terminfo/78/xterm-kitty").exists()
    assert "make" in (home / "events").read_text()
    assert os.environ["DOTFILES_NVIM_BOOTSTRAP"].endswith("/scripts/bootstrap-nvim.lua")
    record("neovim setup")
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
            "uname", "git", "sudo", "dnf", "curl", "uv", "node", "npm",
            "python3", "make", "cargo", "rustc", "rust-analyzer", "go",
            "fzf", "starship", "atuin", "sk", "delta", "bat",
            "fd", "eza", "zsh-autosuggestions", "cargo-sweep", "cargo-cache",
            "gh", "git-crypt", "jq", "yq", "rg", "stylua", "nvim", "shfmt",
            "bash-language-server", "typescript-language-server", "gopls",
            "gotestsum", "ctags-lsp", "tree-sitter", "hexyl", "yaml-language-server",
            "direnv", "just",
        ):
            (fixture / tool).symlink_to(driver)
        env = {
            **os.environ,
            "HOME": str(home),
            "PATH": f"{fixture}:/usr/bin:/bin",
        }
        env.pop("GOPATH", None)
        env.pop("GOBIN", None)
        # Run the real entrypoint from a box with old Python, Node and uv,
        # and a system Rust installation without rustup.
        result = subprocess.run(
            ["/bin/bash", str(checkout / "bootstrap.sh")],
            env=env, capture_output=True, text=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        events = (home / "events").read_text().splitlines()
        assert events.index("make") > max(events.index(tool) for tool in ("uv", "node", "python", "rustup"))
        assert "neovim setup" in events
        assert "atuin setup" in events
        assert "Bootstrap installation completed!" in result.stdout
        print("PASS: fresh-box bootstrap installs working runtimes before linking configuration.")


if __name__ == "__main__":
    main()
