#!/usr/bin/env python3
"""Exercise the native installer with real binaries and no language tools on PATH."""
import argparse
import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    binary = parser.parse_args().binary.resolve()
    version = tomllib.loads((ROOT / 'bootstrap/tools.toml').read_text())['tools']['worktree-policy']['version']
    system = {'Darwin': 'darwin', 'Linux': 'linux'}[platform.system()]
    arch = {'arm64': 'arm64', 'aarch64': 'arm64', 'x86_64': 'amd64', 'amd64': 'amd64'}[platform.machine()]
    name = f'git-worktree-policy-{system}-{arch}'
    with tempfile.TemporaryDirectory(prefix='native-policy-install-') as temporary:
        root = Path(temporary)
        fixtures = root / 'fixtures'
        fixtures.mkdir()
        for tool in ('uname', 'awk', 'sha256sum', 'shasum', 'cp', 'sed', 'mkdir', 'mktemp', 'rm', 'basename', 'chmod', 'mv'):
            source = shutil.which(tool)
            if source:
                (fixtures / tool).symlink_to(source)
        curl = fixtures / 'curl'
        curl.write_text('#!/bin/sh\ncase "$2" in\n  https://github.com/lanej/dotfiles/releases/download/git-worktree-policy-v' + version + '/*) ;;\n  *) exit 9 ;;\nesac\ncp "$POLICY_FIXTURES/$(basename "$2")" "$4"\n')
        curl.chmod(0o755)
        packages = root / 'packages'
        packages.mkdir()
        package = packages / name
        shutil.copyfile(binary, package)
        def checksum(path):
            path.with_name(path.name + '.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n')
        checksum(package)
        home = root / "home with 'quotes"
        env = {**os.environ, 'HOME': str(home), 'PATH': str(fixtures), 'POLICY_FIXTURES': str(packages)}
        env.pop('DOTFILES_WORKTREE_POLICY_BINARY', None)
        def install(*, source=None, success=True):
            selected = {**env}
            if source:
                selected['DOTFILES_WORKTREE_POLICY_BINARY'] = str(source)
            result = subprocess.run(['/bin/sh', str(ROOT / 'scripts/install-worktree-policy'), version], env=selected, text=True, capture_output=True)
            assert (result.returncode == 0) == success, result.stdout + result.stderr
            return result
        install()
        destination = home / '.local/libexec/git-worktree-policy'
        original = destination.read_bytes()
        output = subprocess.check_output([str(ROOT / 'bin/git-worktree-policy'), '--version'], env=env, text=True)
        assert output.strip() == f'git-worktree-policy {version}'
        curl.write_text('#!/bin/sh\nexit 8\n')
        assert 'Using installed' in install().stdout
        bad = root / 'bad-policy'
        shutil.copyfile(binary, bad)
        bad.with_name(bad.name + '.sha256').write_text('0' * 64 + '  ' + bad.name + '\n')
        assert 'checksum mismatch' in install(source=bad, success=False).stderr
        assert destination.read_bytes() == original
        bad.write_text('#!/bin/sh\necho wrong-version\n')
        checksum(bad)
        assert 'version or platform mismatch' in install(source=bad, success=False).stderr
        assert destination.read_bytes() == original
        destination.unlink()
        destination.write_text('user replacement\n')
        assert 'modified' in install(source=package, success=False).stderr
        assert destination.read_text() == 'user replacement\n'
        destination.write_bytes(original)
        destination.chmod(0o755)
        curl.write_text('#!/bin/sh\nprintf "concurrent replacement\\n" > "$HOME/.local/libexec/git-worktree-policy"\ncp "$POLICY_FIXTURES/$(basename "$2")" "$4"\n')
        # Force an update while preserving a valid ownership digest.
        receipt = home / '.local/share/git-worktree-policy/install-receipt'
        receipt.write_text('0.0.0\n' + hashlib.sha256(original).hexdigest() + '\n')
        assert 'changed installation' in install(success=False).stderr
        assert destination.read_text() == 'concurrent replacement\n'
        destination.unlink()
        destination.write_text('user-managed binary\n')
        (home / '.local/share/git-worktree-policy/install-receipt').unlink()
        assert 'unmanaged' in install(source=package, success=False).stderr
        assert destination.read_text() == 'user-managed binary\n'
        destination.unlink()
        destination.symlink_to(binary)
        assert 'unmanaged' in install(source=package, success=False).stderr
        assert destination.is_symlink()
        print('Native installer: verified download, runtime-free execution, reuse, rejection and ownership checks passed')

if __name__ == '__main__':
    main()
