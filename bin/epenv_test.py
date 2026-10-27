"""One acceptance workflow for profile selection through real withenv."""
import os
import json
from pathlib import Path
import shutil
import shlex
import subprocess


def test_profile_command_is_independent_of_the_parent_shell(tmp_path):
    assert shutil.which('ep-direnv'), 'Install ep-direnv to run this detector'
    assert shutil.which('direnv'), 'Install direnv to run this detector'
    assert shutil.which('withenv'), 'Install legacy EasyPost withenv to run this detector'
    program = Path(__file__).with_name('epenv')
    root = tmp_path / 'app'
    child = root / 'nested'
    child.mkdir(parents=True)
    (root / '.env').write_text('MODE=development\nBASE_VALUE=base\n')
    (root / '.env-test').write_text('MODE=test\nDATABASE_URI=fixture_database\nEXPANDED="$BASE_VALUE/test"\n')
    (root / '.env-override').write_text('MODE=wrong\nOVERRIDE_ONLY=yes\n')
    (root / '.env-secrets').write_text('SECRET_ONLY=yes\n')
    (root / 'inherited-extra').write_text('MODE=wrong_extra\n')
    environment = {**os.environ, 'DATABASE_URI': 'parent_database', 'PYTHONPATH': 'parent_python',
                   'ENVFILE': '.env-override', 'EXTRA_ENVFILES': 'inherited-extra', 'MODE': 'parent'}
    home = tmp_path / 'home'
    home.mkdir()
    environment.update({'HOME': str(home), 'XDG_CONFIG_HOME': str(home / '.config'),
                        'XDG_DATA_HOME': str(home / '.local/share'),
                        'XDG_CACHE_HOME': str(home / '.cache'), 'DIRENV_LOG_FORMAT': '',
                        'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'})
    subprocess.run(['git', 'init', '-q'], cwd=root, env=environment, check=True)
    subprocess.run(['git', 'remote', 'add', 'origin', 'git@github.com:EasyPost/fixture.git'],
                   cwd=root, env=environment, check=True)
    subprocess.run(['git', 'add', '.env'], cwd=root, env=environment, check=True)
    environment.pop('IN_SRVENV', None)
    environment.pop('__IN_WITHENV__', None)
    code = '''
    test "$MODE" = test && test "$DATABASE_URI" = fixture_database &&
    test "$EXPANDED" = base/test && test -z "${PYTHONPATH+x}" &&
    test -z "${OVERRIDE_ONLY+x}" && test -z "${SECRET_ONLY+x}" &&
    test "$SERVICEDIR/nested" = "$PWD" && test "$1" = 'argument with spaces' || exit 1
    exit 23
    '''
    result = subprocess.run([str(program), 'test', '/bin/sh', '-c', code, 'test', 'argument with spaces'],
                            cwd=child, env=environment, capture_output=True, text=True)
    assert result.returncode == 23, result.stderr
    envrc = root / '.envrc'
    generated = envrc.read_text()
    assert 'use easypost_legacy' in generated
    assert '.env-test' not in generated, 'per-command profile became shell default'
    status = subprocess.run(['direnv', 'status', '--json'], cwd=root, env=environment,
                            capture_output=True, text=True, check=True)
    assert json.loads(status.stdout)['state']['foundRC']['allowed'] == 0
    ignored = subprocess.run(['git', 'check-ignore', '.envrc'], cwd=root, env=environment)
    assert ignored.returncode == 0
    # Independent invocations rebuild selection; no export in an earlier shell is needed.
    second = subprocess.run([str(program), 'test', '/bin/sh', '-c', 'test "$MODE" = test'],
                            cwd=child, env=environment, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert environment['MODE'] == 'parent'
    assert envrc.read_text() == generated
    other = tmp_path / 'other'
    other.mkdir()
    (other / '.env-alternate').write_text('MODE=wrong_root\n')
    leaked = {**environment, '__IN_WITHENV__': 'leaked', '__ENVFILE__': '.env-alternate',
              '__WITHENV_SERVICEDIR__': str(other), '__WITHENV_HOME__': str(tmp_path),
              '__WITHENV_TERM__': 'dumb'}
    result = subprocess.run([str(program), 'test', '/bin/sh', '-c', code, 'test', 'argument with spaces'],
                            cwd=child, env=leaked, capture_output=True, text=True)
    assert result.returncode == 23, result.stderr
    # Missing profiles must not silently run in the base environment.
    marker = tmp_path / 'unexpected-execution'
    result = subprocess.run([str(program), 'missing', '/usr/bin/touch', str(marker)],
                            cwd=child, env=environment, capture_output=True, text=True)
    assert result.returncode == 2 and not marker.exists()
    # Custom shell defaults and their approval status survive another invocation.
    envrc.write_text('export CUSTOM_SHELL_DEFAULT=yes\n')
    result = subprocess.run([str(program), 'test', '/bin/sh', '-c', 'test "$MODE" = test'],
                            cwd=child, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert envrc.read_text() == 'export CUSTOM_SHELL_DEFAULT=yes\n'
    status = subprocess.run(['direnv', 'status', '--json'], cwd=root, env=environment,
                            capture_output=True, text=True, check=True)
    assert json.loads(status.stdout)['state']['foundRC']['allowed'] != 0

    # A setup failure is explicit and cannot execute the requested command.
    shim = tmp_path / 'failed-setup'
    shim.mkdir()
    helper = shim / 'ep-direnv'
    helper_invoked = tmp_path / 'helper-invoked'
    helper.write_text('#!/bin/sh\n: > ' + shlex.quote(str(helper_invoked)) + '\nexit 42\n')
    helper.chmod(0o755)
    failed_environment = {**environment, 'PATH': str(shim) + ':' + environment['PATH']}
    existing = subprocess.run([str(program), 'test', '/bin/sh', '-c', 'test "$MODE" = test'],
                              cwd=child, env=failed_environment, capture_output=True, text=True)
    assert existing.returncode == 0 and not helper_invoked.exists()
    envrc.unlink()
    result = subprocess.run([str(program), 'test', '/usr/bin/touch', str(marker)],
                            cwd=child, env=failed_environment, capture_output=True, text=True)
    assert result.returncode == 1 and not marker.exists()
    assert 'setup failed' in result.stderr
    assert helper_invoked.exists()
    helper_invoked.unlink()
    result = subprocess.run([str(program), 'test', '/usr/bin/touch', str(marker)],
                            cwd=child, env={**failed_environment, 'IN_SRVENV': '1'},
                            capture_output=True, text=True)
    assert result.returncode == 1 and not helper_invoked.exists() and not marker.exists()
    assert 'inside srvenv' in result.stderr
