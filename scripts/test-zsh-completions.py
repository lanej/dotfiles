#!/usr/bin/env python3
"""Configure installed completions, safely refresh them, then use recomp in Zsh."""
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent.parent


def main():
    with tempfile.TemporaryDirectory(prefix="dotfiles-completions-") as temporary:
        temporary = Path(temporary).resolve()
        home = temporary / "home with spaces"
        executables = temporary / "bin"
        home.mkdir()
        executables.mkdir()
        (home / ".files").symlink_to(ROOT)
        # Only system utilities and the tools installed during this workflow are
        # visible. In particular, setup cannot depend on Python or Zsh itself.
        for name in ("awk", "bash", "cat", "chmod", "cmp", "dirname", "grep",
                     "head", "ln", "mkdir", "mktemp", "mv", "pwd", "rm", "sed",
                     "sort", "touch", "tr", "uname"):
            (executables / name).symlink_to(shutil.which(name))
        env = {"HOME": str(home), "ZDOTDIR": str(home), "PATH": str(executables),
               "TERM": "dumb", "LC_ALL": "C", "TMPDIR": str(temporary)}
        command = [shutil.which("make"), "--no-print-directory"]

        def make(target="zsh-completions", *, success=True):
            result = subprocess.run([*command, target], cwd=ROOT, env=env,
                                    capture_output=True, text=True, timeout=30)
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            return result

        make("zsh-config")
        completions = home / ".zsh/completions"
        assert not list(completions.iterdir()), "missing optional tools should be skipped"
        custom = completions / "_gh"
        custom.write_text("#compdef gh\n# My custom completion\n")
        linked_source = home / "custom uv"
        linked_source.write_text("#compdef uv\n# My symlinked completion\n")
        (completions / "_uv").symlink_to(linked_source)
        gh = executables / "gh"
        gh.write_text("#!/bin/sh\necho 'custom gh must not be overwritten' >&2\nexit 1\n")
        gh.chmod(0o755)
        (executables / "uv").symlink_to(gh)
        epf = executables / "epf"
        epf.write_text('''#!/bin/sh
[ "$*" = 'completions zsh' ] || exit 7
printf '#compdef epf\nprint -r -- completion-v1\n'
''')
        epf.chmod(0o755)
        cache = home / ".zcompdump"
        compiled_cache = home / ".zcompdump.zwc"
        cache.write_text("stale")
        compiled_cache.write_text("stale compiled cache")
        preview = subprocess.run([*command, "-n", "zsh-completions"], cwd=ROOT,
                                 env=env, capture_output=True, text=True, timeout=30)
        assert preview.returncode == 0 and cache.exists() and not (completions / "_epf").exists()
        make("zsh-config")
        generated = completions / "_epf"
        original = generated.read_bytes()
        stamp = generated.stat().st_mtime_ns
        assert b"completion-v1" in original and not cache.exists() and not compiled_cache.exists()
        assert "My custom" in custom.read_text() and (completions / "_uv").is_symlink()
        assert "My symlinked" in linked_source.read_text()
        cache.write_text("keep unchanged cache")
        make()
        assert generated.read_bytes() == original and generated.stat().st_mtime_ns == stamp
        assert cache.read_text() == "keep unchanged cache", "no-op setup must keep the cache"

        # An interrupted/failed generator must not truncate the working file.
        epf.write_text("#!/bin/sh\nprintf '#compdef epf\\npartial\\n'\nexit 1\n")
        failed = make(success=False)
        assert "previous completion kept" in failed.stderr
        assert generated.read_bytes() == original and cache.exists()
        epf.write_text("#!/bin/sh\nexit 0\n")
        empty = make(success=False)
        assert "Invalid or empty" in empty.stderr and generated.read_bytes() == original
        assert not list(completions.glob(".epf.*")), "failed generators must clean staging files"

        # Load the real shell configuration with no system optional tools. Avoid
        # profile-driven PATH additions; this workflow is about completions.
        profile = home / ".profile"
        profile.unlink()
        profile.write_text("")
        (executables / "zsh").symlink_to(shutil.which("zsh"))
        cache.unlink()
        epf.write_text("#!/bin/sh\nprintf '#compdef epf\\nprint -r -- completion-v2\\n'\n")
        probe = '''
[[ $_comps[epf] == _epf ]] || exit 10
[[ $(_epf) == completion-v1 ]] || exit 11
recomp || exit 12
[[ $_comps[epf] == _epf ]] || exit 13
[[ $(_epf) == completion-v2 ]] || exit 14
[[ -f $HOME/.zcompdump ]] || exit 15
print -r -- READY
'''
        refreshed = subprocess.run([shutil.which("zsh"), "-d", "-i", "-c", probe],
                                   cwd=home, env=env, capture_output=True, text=True, timeout=30)
        assert refreshed.returncode == 0, refreshed.stdout + refreshed.stderr
        assert refreshed.stdout.endswith("READY\n") and refreshed.stderr == "", refreshed
        assert not (home / ".local/share/fzf-tab").exists(), "recomp must not install plugins"
        assert not (home / ".ssh/agent-env").exists(), "setup must not start shell services"
        print("PASS: installed completions refresh safely and recomp reloads the active shell.")


if __name__ == "__main__":
    main()
