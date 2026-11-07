#!/usr/bin/env python3
"""Diagnostic branch only: instrument an exact copy of the installed fork."""
import os
from pathlib import Path
import shutil
import subprocess

revision = 'dfc4f414c1a9386b07911ebd3cfb4e7aaa4289f5'
cargo_home = Path(os.environ.get('CARGO_HOME', Path.home() / '.cargo'))
sources = []
for candidate in (cargo_home / 'git/checkouts').glob('zellij-*/*'):
    if (candidate / 'zellij-server').is_dir():
        head = subprocess.check_output(['git', '-C', str(candidate), 'rev-parse', 'HEAD'], text=True).strip()
        if head == revision:
            sources.append(candidate)
assert len(sources) == 1, sources
source = Path(os.environ['RUNNER_TEMP']) / 'popup-native-source'
shutil.copytree(sources[0], source, ignore=shutil.ignore_patterns('.git', 'target'))
patch = Path(__file__).with_name('popup-native.patch').resolve()
subprocess.run(['git', 'apply', '--check', str(patch)], cwd=source, check=True)
subprocess.run(['git', 'apply', str(patch)], cwd=source, check=True)
env = dict(os.environ)
env.update(CARGO_TARGET_DIR=str(Path.home() / '.cache/dotfiles/zellij/target'),
           CARGO_PROFILE_RELEASE_LTO='false', CARGO_PROFILE_RELEASE_CODEGEN_UNITS='16',
           CARGO_BUILD_JOBS='2')
host = next(line.split(': ', 1)[1] for line in subprocess.check_output(
    ['rustup', 'run', '1.95.0', 'rustc', '-vV'], text=True).splitlines() if line.startswith('host: '))
subprocess.run(['rustup', 'run', '1.95.0', 'cargo', 'install', '--path', str(source),
                '--locked', '--force', '--root', str(Path.home() / '.local'), '--target', host,
                '--no-default-features', '--features', 'plugins_from_target,vendored_curl,web_server_capability',
                '--bin', 'zellij'], env=env, check=True)
