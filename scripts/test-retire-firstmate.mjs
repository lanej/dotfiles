import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, readFile, symlink, lstat, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const root = dirname(dirname(fileURLToPath(import.meta.url)));
await test('retirement is idempotent and preserves unrelated configuration and saved work', async () => {
 const home = await mkdtemp(join(tmpdir(), 'retire-firstmate-'));
 try {
  for (const directory of ['.pi/agent','.paseo','.local/bin','src/firstmate/state']) await mkdir(join(home,directory),{recursive:true});
  const module = name => join(root,'pi/extensions/firstmate-'+name+'.mjs');
  await writeFile(join(home,'.pi/agent/settings.json'),JSON.stringify({model:'keep',extensions:[module('github'),module('tasks'),module('peers'),module('questions'),module('bedrock-router'),'unrelated']}));
  await writeFile(join(home,'.paseo/config.json'),JSON.stringify({agents:{providers:{firstmate:{command:[join(root,'bin/firstmate'),'rpc']},pi:{enabled:true}}}}));
  await writeFile(join(home,'src/firstmate/state/task.json'),'saved work');
  await symlink(join(root,'bin/firstmate'),join(home,'.local/bin/firstmate'));
  for(let i=0;i<2;i++) execFileSync(process.execPath,[join(root,'scripts/retire-firstmate.mjs'),home],{env:{...process.env,PASEO_HOME:join(home,'.paseo')}});
  const settings=JSON.parse(await readFile(join(home,'.pi/agent/settings.json'),'utf8'));
  assert.deepEqual(settings.extensions,[module('questions'),module('bedrock-router'),'unrelated']);
  assert.equal(settings.model,'keep');
  assert.deepEqual(JSON.parse(await readFile(join(home,'.paseo/config.json'),'utf8')).agents.providers,{pi:{enabled:true}});
  assert.equal(await readFile(join(home,'src/firstmate/state/task.json'),'utf8'),'saved work');
  await assert.rejects(lstat(join(home,'.local/bin/firstmate')),{code:'ENOENT'});
 } finally {await rm(home,{recursive:true,force:true});}
});
