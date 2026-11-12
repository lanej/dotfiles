#!/usr/bin/env python3
"""Check opt-in installation and configured provider selection through real Git."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--git', type=Path, required=True)
    args = parser.parse_args()
    version = tomllib.loads((ROOT/'bootstrap/tools.toml').read_text())['tools']['worktree-manager']['version']
    with tempfile.TemporaryDirectory(prefix='dotfiles-worktree-manager-') as temporary:
        root = Path(temporary).resolve()
        home = root / "home with 'quotes"
        home.mkdir()
        fixture = root/'dotfiles'
        fixture.mkdir()
        for name in ('Makefile','scripts','config','bootstrap','git','bin','design-system','worktree-manager'):
            (fixture/name).symlink_to(ROOT/name)
        git = args.git.resolve()
        machine = home/'machine.toml'
        machine.write_text('[tools]\nworktree-manager = true\nworktree-policy = true\n')
        env = {k:v for k,v in os.environ.items() if not k.startswith(('GIT_','XDG_','WORKTREE_','DOTFILES_'))}
        env.update(HOME=str(home), PATH=str(git.parent)+os.pathsep+env['PATH'],
                   DOTFILES_CONFIG=str(machine), GIT_CONFIG_GLOBAL=str(home/'.gitconfig'), GIT_CONFIG_NOSYSTEM='1',
                   XDG_CONFIG_HOME=str(home/"custom-config with 'quotes"), XDG_STATE_HOME=str(home/'state[1]'))
        def run(*argv, cwd=fixture, ok=True, extra=None):
            result = subprocess.run([str(a) for a in argv], cwd=cwd, env={**env, **(extra or {})}, text=True, capture_output=True, timeout=90)
            assert (result.returncode==0)==ok, (argv,result.returncode,result.stdout,result.stderr)
            return result
        run(git,'init','-q',fixture)
        run('/bin/sh',ROOT/'scripts/install-worktree-manager',version,extra={'WORKTREE_INSTALL_BINARY':str(args.binary.resolve())})
        run('make','--no-print-directory','configure','SELECTED_TARGETS=git')
        legacy = home/'.local/bin/git-worktree-policy'
        assert run(legacy,'--version').stdout.strip()==f'git-worktree-policy {version}'
        settings = Path(env['XDG_CONFIG_HOME'])/'worktree-manager/config.json'
        assert json.loads(settings.read_text())=={'recovery_allowed_github_owners':['easypost-sandbox']}
        settings.write_text('{"recovery_allowed_github_owners": []}\n')
        run('make','--no-print-directory','configure','SELECTED_TARGETS=git')
        assert settings.read_text()=='{"recovery_allowed_github_owners": []}\n'
        repo = root/'project'
        run(git,'init','-q','--initial-branch=main',repo)
        run(git,'-c','user.name=Test','-c','user.email=test@example.invalid','-c','commit.gpgsign=false','commit','--allow-empty','-qm','initial',cwd=repo)
        run(legacy,'configure','--global','--max-worktrees','1',cwd=repo)
        run(git,'worktree','add','--no-checkout','-b','first',root/'first',cwd=repo)
        denied = run(git,'worktree','add','--no-checkout','-b','blocked',root/'blocked',cwd=repo,ok=False)
        assert 'refusing add' in denied.stderr and not (root/'blocked').exists()
        run(git,'remote','add','origin','https://github.com/easypost-sandbox/worktree-manager-fixture.git',cwd=repo)
        settings.write_text('{"recovery_allowed_github_owners": ["easypost-sandbox"]}\n')
        preview = run(home/'.local/bin/worktree','prune','--json','--wip-push','--accept-recent','--worktree',root/'first',cwd=repo)
        rows = json.loads(preview.stdout)['result']['worktrees']
        assert next(row for row in rows if row['path']==str(root/'first'))['action']=='wip-push'
        settings.write_text('{"recovery_allowed_github_owners": []}\n')
        declined = run(home/'.local/bin/worktree','prune','--json','--wip-push','--accept-recent','--worktree',root/'first',cwd=repo)
        assert 'no approved push remote' in declined.stdout
        installed = home/'.local/bin/worktree'
        saved = root/'saved-binary'
        installed.rename(saved)
        missing = run(git,'worktree','add','--no-checkout','-b','missing',root/'missing',cwd=repo,ok=False)
        assert 'selected worktree manager is unavailable' in missing.stderr
        checkout = run(git,'checkout','main',cwd=repo)
        assert 'selected worktree manager is unavailable' in checkout.stderr
        saved.rename(installed)
        machine.write_text('[tools]\nworktree-manager = false\nworktree-policy = true\n')
        run('make','--no-print-directory','configure','SELECTED_TARGETS=git')
        fallback = run(legacy,'preflight',cwd=repo,ok=False)
        assert 'native policy is unavailable' in fallback.stderr
        machine.write_text('[tools]\nworktree-manager = false\nworktree-policy = false\n')
        run('make','--no-print-directory','configure','SELECTED_TARGETS=git')
        run(git,'worktree','add','--no-checkout','-b','disabled',root/'disabled',cwd=repo)
        assert settings.read_text()=='{"recovery_allowed_github_owners": []}\n'
        print('Opt-in worktree: installation, provider preference/fallback, global cap, missing-helper safety, opt-out and config preservation passed')


if __name__=='__main__':
    main()
