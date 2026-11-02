#!/usr/bin/env python3
"""Acceptance workflow using real Git, direnv, and zsh in an isolated home."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
DIRENV = subprocess.check_output(['which', 'direnv'], text=True).strip()


def run(*args, cwd=None, env=None, check=True):
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if check and result.returncode:
        raise AssertionError((args, result.returncode, result.stdout, result.stderr))
    return result


def workflow():
    with tempfile.TemporaryDirectory(prefix='ep-direnv-test-') as tmp:
        base = Path(tmp)
        home = base / 'home'
        home.mkdir()
        machine_bin = base / 'machine-bin'
        machine_bin.mkdir()
        withenv = machine_bin / 'withenv'
        withenv.write_text('#!/bin/sh\nexit 0\n')
        withenv.chmod(0o755)
        lib = home / '.config/direnv/lib'
        lib.mkdir(parents=True)
        (lib / 'easypost_legacy.sh').symlink_to(SOURCE / 'direnv/easypost_legacy.sh')
        env = {**os.environ, 'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
               'XDG_DATA_HOME': str(home / '.local/share'), 'XDG_CACHE_HOME': str(home / '.cache'),
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1',
               'PATH': str(machine_bin) + ':' + str(SOURCE / 'bin') + ':' + str(Path(DIRENV).parent) + ':' + os.environ['PATH'],
               'DIRENV_LOG_FORMAT': '', 'KEEP_PARENT': 'present'}
        for key in ('DIRENV_DIR', 'DIRENV_DIFF', 'DIRENV_WATCHES', 'ENVFILE', 'EXTRA_ENVFILES', 'IN_SRVENV'):
            env.pop(key, None)
        repo = base / 'app'
        repo.mkdir()
        def git(*args, cwd=repo, check=True):
            return run('git', *args, cwd=cwd, env=env, check=check)
        def setup(action='ensure', cwd=repo):
            return run(str(SOURCE / 'bin/ep-direnv'), action, str(cwd), cwd=cwd, env=env)
        def export(cwd=repo, extra=None):
            result = run(DIRENV, 'export', 'json', cwd=cwd, env={**env, **(extra or {})}, check=False)
            return json.loads(result.stdout or '{}')
        git('init', '-q')
        git('config', 'user.email', 'test@example.com')
        git('config', 'user.name', 'Test')
        (repo / '.env').write_text('ORDER=base\nEXPANDED="$KEEP_PARENT/base"\n')
        git('add', '.env')
        git('commit', '-qm', 'fixture')
        setup()
        assert not (repo / '.envrc').exists(), 'non-EasyPost repository changed'
        git('remote', 'add', 'origin', 'git@github.com:EasyPost/legacy.git')
        # Default hooks compose without consuming stdin or changing cwd.
        hooks = repo / '.git/hooks'
        (hooks / 'post-checkout').write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" >> "$HOME/checkouts"\nexit 7\n')
        (hooks / 'pre-push').write_text('#!/bin/sh\ncat > "$HOME/hook-input"\nexit 9\n')
        (hooks / 'post-checkout').chmod(0o755)
        (hooks / 'pre-push').chmod(0o755)
        setup()
        content = (repo / '.envrc').read_text()
        setup()
        assert (repo / '.envrc').read_text() == content
        assert git('check-ignore', '.envrc').returncode == 0
        assert export()['EXPANDED'] == 'present/base'
        dispatcher = git('config', '--get', 'core.hooksPath').stdout.strip()
        result = subprocess.run([dispatcher + '/pre-push', 'remote', 'url'], input='stdin preserved\n',
                                text=True, capture_output=True, cwd=repo, env=env)
        assert result.returncode == 9 and (home / 'hook-input').read_text() == 'stdin preserved\n'
        (repo / '.env-build').write_text('ORDER="$ORDER/build"\n')
        (repo / '.env-runtime').write_text('ORDER="$ORDER/runtime"\n')
        (repo / '.env-override').write_text('ORDER="$ORDER/override"\nSHARED=primary\n')
        (repo / '.env-secrets').write_text('ORDER="$ORDER/secrets"\n')
        assert export()['ORDER'] == 'base/build/runtime/override/secrets'
        (repo / 'extra').write_text('ORDER="$ORDER/extra"\n')
        assert export(extra={'ENVFILE': '.env-runtime', 'EXTRA_ENVFILES': 'extra'})['ORDER'] == '/runtime/extra'
        wt = base / 'worktree'
        result = git('worktree', 'add', '-b', 'linked', str(wt), check=False)
        assert result.returncode != 0, 'original post-checkout failure lost'
        assert (wt / '.envrc').read_text() == content, 'new worktree not set up'
        receipt = (home / 'checkouts').read_text().splitlines()
        assert receipt[0] == str(wt)
        assert receipt[1] == '0' * 40 and len(receipt[2]) == 40 and receipt[3] == '1'
        assert export(wt)['SHARED'] == 'primary'
        (wt / '.env-override').write_text('SHARED=local\n')
        assert export(wt)['SHARED'] == 'local'
        (wt / '.env-override').unlink()
        (repo / '.env-override').write_text('SHARED=updated\n')
        assert export(wt)['SHARED'] == 'updated'
        # Reload in the same shell as watched missing/local/fallback files change.
        reload_shell = r'''set -e
        eval "$(direnv export bash)"
        test "$SHARED" = updated
        sleep 1
        echo SHARED=appeared > .env-override
        eval "$(direnv export bash)"
        test "$SHARED" = appeared
        sleep 1
        rm .env-override
        echo SHARED=reloaded > "$1/.env-override"
        eval "$(direnv export bash)"
        test "$SHARED" = reloaded
        '''
        run('bash', '-c', reload_shell, 'test', str(repo), cwd=wt, env=env)
        (repo / '.env-override').write_text('SHARED=updated\n')
        # A parent shell export/unexport restores its environment on exit.
        shell = 'eval "$(direnv export bash)"; test "$SHARED" = updated; test "$KEEP_PARENT" = present; cd "$HOME"; eval "$(direnv export bash)"; test -z "${SHARED+x}"; test "$KEEP_PARENT" = present'
        run('bash', '-c', 'set -e; ' + shell, cwd=wt, env=env)
        # The installed zsh entrypoint handles startup and later directory entry.
        lazy = SOURCE / 'zsh/lazy-load.zsh'
        if not lazy.exists():
            lazy = SOURCE / 'lazy-load.zsh'
        personal_bin = base / 'personal-bin'
        personal_bin.mkdir()
        for tool in ('direnv', 'bash', 'zsh', 'sh', 'dirname', 'readlink', 'rm'):
            (personal_bin / tool).symlink_to(run('which', tool).stdout.strip())
        personal_env = {**env, 'PATH': str(personal_bin)}
        shell = 'source "$1"; (( $+functions[_direnv_hook] )) && (( ! $+functions[_ep_direnv_enter] )) && (( ${chpwd_functions[(Ie)_direnv_hook]} ))'
        run('zsh', '-f', '-i', '-c', shell, 'test', str(lazy), cwd=home, env=personal_env)
        shell = 'source "$1"; test "$SHARED" = updated || exit 2; cd "$HOME"; test -z "${SHARED+x}" || exit 3; cd "$2"; test "$SHARED" = updated'
        run('zsh', '-f', '-i', '-c', shell, 'test', str(lazy), str(wt), cwd=wt, env=env)
        shell = 'source "$1"; cd "$2"; test "$SHARED" = updated'
        run('zsh', '-f', '-i', '-c', shell, 'test', str(lazy), str(wt), cwd=home, env=env)
        assert not export(wt, {'IN_SRVENV': '1'}).get('SHARED')
        (wt / '.env-override').write_text('echo DO_NOT_PRINT\nreturn 1\n')
        failure = run(DIRENV, 'export', 'json', cwd=wt, env=env, check=False)
        assert 'DO_NOT_PRINT' not in failure.stdout + failure.stderr
        assert not json.loads(failure.stdout or '{}').get('SHARED')
        (wt / '.env-override').unlink()
        setup('uninstall')
        assert git('config', '--local', '--get', 'core.hooksPath', check=False).returncode == 1
        no_checkout = base / 'no-checkout'
        git('worktree', 'add', '--no-checkout', '-b', 'no-checkout', str(no_checkout))
        assert not (no_checkout / '.envrc').exists()
        setup(cwd=no_checkout)
        assert (no_checkout / '.envrc').read_text() == content
        setup('uninstall')
        disabled = base / 'disabled'
        git('-c', 'core.hooksPath=/dev/null', 'worktree', 'add', '-b', 'disabled', str(disabled))
        assert not (disabled / '.envrc').exists()
        setup(cwd=disabled)
        assert (disabled / '.envrc').read_text() == content
        setup('uninstall')
        # Relative custom and worktree-specific hooks retain their own context.
        for checkout in (repo, wt):
            custom = checkout / ('custom-hooks' if checkout == repo else 'worktree-hooks')
            custom.mkdir()
            hook = custom / 'post-checkout'
            hook.write_text('#!/bin/sh\npwd > "$HOME/relative-hook"\n')
            hook.chmod(0o755)
        git('config', 'core.hooksPath', 'custom-hooks')
        git('config', 'extensions.worktreeConfig', 'true')
        git('config', '--worktree', 'core.hooksPath', 'worktree-hooks', cwd=wt)
        setup()
        git('checkout', 'linked', cwd=wt)
        assert (home / 'relative-hook').read_text().strip() == str(wt)
        setup('uninstall')
        assert git('config', '--local', '--get', 'core.hooksPath').stdout.strip() == 'custom-hooks'
        assert git('config', '--worktree', '--get', 'core.hooksPath', cwd=wt).stdout.strip() == 'worktree-hooks'
        # Git expands home-relative hook paths; forwarding must do the same.
        custom = home / 'custom-hooks'
        custom.mkdir()
        hook = custom / 'pre-commit'
        hook.write_text('#!/bin/sh\nprintf preserved > "$HOME/home-hook"\nexit 8\n')
        hook.chmod(0o755)
        git('config', 'core.hooksPath', '~/custom-hooks')
        setup()
        result = git('commit', '--allow-empty', '-m', 'blocked', check=False)
        assert result.returncode != 0 and (home / 'home-hook').read_text() == 'preserved'
        setup('uninstall')
        assert git('config', '--get', 'core.hooksPath').stdout.strip() == '~/custom-hooks'
        # Existing custom, symlinked and tracked files are never approved or rewritten.
        (repo / '.envrc').write_text('export CUSTOM=yes\n')
        setup()
        assert (repo / '.envrc').read_text() == 'export CUSTOM=yes\n'
        assert not export().get('CUSTOM')
        (repo / '.envrc').unlink()
        target = repo / 'custom-envrc'
        target.write_text(content)
        (repo / '.envrc').symlink_to(target)
        setup()
        assert (repo / '.envrc').is_symlink()
        (repo / '.envrc').unlink()
        (repo / '.envrc').write_text(content)
        git('add', '-f', '.envrc')
        setup()
        # Preserve changes to hook configuration made after installation.
        git('config', 'core.hooksPath', 'later-user-hooks')
        setup('uninstall')
        assert git('config', '--local', '--get', 'core.hooksPath').stdout.strip() == 'later-user-hooks'
        # Later multi-valued settings can still select our dispatcher. Retain it.
        later_hooks = repo / 'later-user-hooks'
        later_hooks.mkdir()
        later_hook = later_hooks / 'post-checkout'
        later_hook.write_text('#!/bin/sh\npwd > "$HOME/relative-hook"\n')
        later_hook.chmod(0o755)
        setup()
        dispatcher = git('config', '--get', 'core.hooksPath').stdout.strip()
        git('config', '--unset-all', 'core.hooksPath')
        git('config', '--add', 'core.hooksPath', 'later-user-hooks')
        git('config', '--add', 'core.hooksPath', dispatcher)
        setup('uninstall')
        assert Path(dispatcher).is_dir()
        git('checkout', git('branch', '--show-current').stdout.strip())
        assert (home / 'relative-hook').read_text().strip() == str(repo)
        git('config', '--unset-all', 'core.hooksPath')
        setup('uninstall')
        # Simulate replacement exactly at the approval boundary, using real direnv.
        import importlib.machinery
        import importlib.util
        loader = importlib.machinery.SourceFileLoader('ep_direnv', str(SOURCE / 'bin/ep-direnv'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        (repo / '.envrc').write_text('export RACE_EXECUTED=yes\n')
        saved_environment = os.environ.copy()
        try:
            os.environ.update(env)
            module.approve_generated(repo / '.envrc')
        finally:
            os.environ.clear()
            os.environ.update(saved_environment)
        assert not export().get('RACE_EXECUTED'), 'replacement code automatically approved'
        # Installer preserves foreign files, converges, and removes only owned links.
        install_home = base / 'install-home'
        destination = install_home / '.local/bin/ep-direnv'
        destination.parent.mkdir(parents=True)
        destination.write_text('user-owned\n')
        installer = str(SOURCE / 'scripts/install-ep-direnv.sh')
        assert run('sh', installer, 'install', str(SOURCE), str(install_home), check=False).returncode != 0
        assert destination.read_text() == 'user-owned\n'
        destination.unlink()
        run('sh', installer, 'install', str(SOURCE), str(install_home))
        run('sh', installer, 'install', str(SOURCE), str(install_home))
        assert destination.is_symlink()
        run('sh', installer, 'install', str(SOURCE), str(install_home), env=personal_env)
        assert not destination.exists()
        assert not (install_home / '.config/direnv/lib/easypost_legacy.sh').exists()
        run('sh', installer, 'install', str(SOURCE), str(install_home))
        destination.unlink()
        destination.write_text('later-user-file\n')
        run('sh', installer, 'uninstall', str(SOURCE), str(install_home))
        assert destination.read_text() == 'later-user-file\n'
        assert not (install_home / '.config/direnv/lib/easypost_legacy.sh').exists()
        print('ep-direnv acceptance workflow passed')


if __name__ == '__main__':
    workflow()
