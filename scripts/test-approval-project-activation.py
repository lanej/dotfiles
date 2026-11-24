#!/usr/bin/env python3
"""Protect approval adapter staging, routing, pairing and independent inventory."""
import hashlib,json,os,pathlib,subprocess,sys,tempfile
adapter=str(pathlib.Path(__file__).resolve().with_name('approval-project-activation.py'))
with tempfile.TemporaryDirectory(prefix='approval-adapter-') as name:
 base=pathlib.Path(name); prefix=base/'prefix'; binary=prefix/'bin/intent'; binary.parent.mkdir(parents=True)
 profile_list=[{'profile_path':str(base/host),'host':host,'remote_directory':'/broker','local_socket':'/local-'+host,'mac_id':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'} for host in ('dev','dev2')]
 binary.write_text(f'''#!{sys.executable}
import hashlib,json,pathlib,sys
if sys.argv[1:]==['lifecycle','artifact']: print(json.dumps({{'expected_identity':'build:local-selected','sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}}))
elif sys.argv[1:]==['lifecycle','profiles']: print({json.dumps(json.dumps(profile_list))})
elif sys.argv[1:3]==['lifecycle','inventory']:
 profile=pathlib.Path(sys.argv[sys.argv.index('--profile')+1]).name
 print(json.dumps({{'schema_version':1,'targets':[{{'target':'local:/local-'+profile,'mac_id':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','expected_identity':'build:local-selected','running_identity':'build:local-selected','ready':True,'process':{{'pid':10 if profile=='dev' else 11,'start_identity':'local-start-'+profile,'native_id':'local-native-'+profile,'owner_verified':True}},'sessions':[]}}]}}))
else: sys.exit('unexpected local lifecycle mutation')
'''); binary.chmod(0o755)
 tools=base/'tools'; tools.mkdir(); ssh=tools/'ssh'
 ssh.write_text(f'''#!{sys.executable}
import hashlib,json,os,shlex,sys
assert 'ClearAllForwardings=yes' in sys.argv and 'PermitLocalCommand=no' in sys.argv
host=sys.argv[-2]; argv=shlex.split(sys.argv[-1])
if host==os.environ.get('UNREACHABLE_HOST'): sys.exit(255)
if argv==['uname','-sm']: print('Linux x86_64')
elif argv[1:3]==['lifecycle','inventory']:
 print(json.dumps({{'schema_version':1,'targets':[{{'target':'remote:fixture-machine:/broker','expected_identity':'build:old-remote','running_identity':'build:old-remote','ready':True,'platform':'linux','architecture':'amd64','executable':'/old/intent','mac_id':'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb' if os.environ.get('WRONG_PAIR') else 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','process':{{'pid':20,'start_identity':'remote-start','native_id':'remote-native','owner_verified':True}},'sessions':[]}}]}}))
else: sys.exit('unexpected remote lifecycle mutation')
'''); ssh.chmod(0o755)
 scripts=base/'scripts'; scripts.mkdir(); build=scripts/'build-lifecycle.py'
 build.write_text('''import hashlib,json,pathlib,sys
args=sys.argv; output=pathlib.Path(args[args.index('--output')+1]); manifest=pathlib.Path(args[args.index('--manifest')+1]); output.parent.mkdir(parents=True,exist_ok=True); output.write_bytes(b'verified-platform-fixture'); manifest.write_text(json.dumps({'expected_identity':'build:remote-selected','sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'platform':'linux','architecture':'amd64'}))
''')
 env={**os.environ,'HOME':name,'APPROVAL_PROJECT_PREFIX':str(prefix),'XDG_STATE_HOME':str(base/'state'),'XDG_CACHE_HOME':str(base/'cache'),'PATH':str(tools)+os.pathsep+os.environ['PATH']}
 def call(action,expected=0,extra=None):
  result=subprocess.run([sys.executable,adapter,'intent',action],cwd=base,env={**env,**(extra or {})},text=True,capture_output=True)
  assert result.returncode==expected,(result.stdout,result.stderr)
  return json.loads(result.stdout)
 operation_root=base/'state/dotfiles/project-update'
 call('inventory')
 assert not operation_root.exists(), 'Read-only inventory created update state'
 staged=call('stage-remotes'); assert set(staged['remotes'])=={'dev','dev2'}
 assert operation_root.stat().st_mode&0o777==0o700, 'Staging left a public operation root'
 assert (operation_root/'approval-artifacts').stat().st_mode&0o777==0o700
 assert (operation_root/'approval-artifacts/intent.json').stat().st_mode&0o777==0o600
 assert staged['remotes']['dev']==staged['remotes']['dev2']
 targets=call('inventory')['targets']; assert len(targets)==3,targets
 remote=next(row for row in targets if row.get('activation_kind')=='remote'); assert remote['aliases']==['dev','dev2'] and remote['expected_identity']=='build:remote-selected'
 unavailable=call('inventory',extra={'UNREACHABLE_HOST':'dev2'})['targets']; assert len(unavailable)==4,unavailable
 assert unavailable[-1]['process'] is None and unavailable[-1]['reason']=='native-control-unavailable',unavailable
 paired=next(row for row in call('inventory',extra={'WRONG_PAIR':'1'})['targets'] if row.get('activation_kind')=='remote'); assert not paired['ready'] and paired['reason']=='configured-remote-profile-pairing-differs',paired
 operation=base/'operation'; operation.mkdir(mode=0o700); frozen=operation/'intent-inventory.json'; frozen.write_text(json.dumps({'schema_version':1,'targets':[remote]})); frozen.chmod(0o600)
 guarded={'WRONG_PAIR':'1','PROJECT_UPDATE_OPERATION_DIR':str(operation),'PROJECT_UPDATE_TARGET':remote['target'],'PROJECT_UPDATE_RUN_ID':'11111111-2222-4333-8444-555555555555'}
 for action in ('checkpoint','restart'):
  refused=call(action,expected=3,extra=guarded); assert refused['targets'][0]['reason']=='native-pairing-or-process-incarnation-differs',refused
 selected=pathlib.Path(remote['selected_binary']); selected.write_bytes(b'foreign-replacement')
 changed=next(row for row in call('inventory')['targets'] if row.get('activation_kind')=='remote'); assert changed['expected_identity'] is None and changed['reason']=='selected-remote-artifact-changed',changed
 print(json.dumps({'result':'PASS','checks':['all configured dev/dev2 profile rows','local platform staging before deployment','same-broker alias deduplication','unreachable remote preserves independent inventory','tampered staged remote artifact refusal']}))
