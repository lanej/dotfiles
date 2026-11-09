import { test } from 'bun:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, readdir, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { CodexSessionReference, createWorkerRuntime } from '../src/auth.js';
import type { CredentialStore } from '@earendil-works/pi-ai';

const now = 1700000000000;
function accessToken(exp = now / 1000 + 3600) { return `header.${Buffer.from(JSON.stringify({ exp, 'https://api.openai.com/auth': { chatgpt_account_id: 'test-account' } })).toString('base64url')}.signature`; }
function auth(access = accessToken()) { return JSON.stringify({ auth_mode: 'chatgpt', tokens: { access_token: access, refresh_token: 'refresh-must-never-be-used', id_token: 'identity-must-never-be-used' }, preserved: 'unchanged' }); }
async function fixture(run: (directory: string) => Promise<void>) {
  const directory = await mkdtemp(join(tmpdir(), 'pg-auth-'));
  try { await run(directory); } finally { await rm(directory, { recursive: true, force: true }); }
}
test('existing Codex auth is referenced in memory without copying refresh or identity tokens', async () => fixture(async directory => {
  const bytes = auth(); await writeFile(join(directory, 'auth.json'), bytes);
  const store = new CodexSessionReference(directory, () => now);
  const value = await store.read('openai-codex');
  assert.equal(value?.type, 'oauth');
  if (value?.type !== 'oauth') assert.fail('Expected OAuth reference');
  assert.equal(value.access, accessToken()); assert.equal(value.refresh, '');
  assert.equal(JSON.stringify(value).includes('refresh-must-never-be-used'), false);
  assert.equal(JSON.stringify(value).includes('identity-must-never-be-used'), false);
  assert.deepEqual(await store.list(), [{ providerId: 'openai-codex', type: 'oauth' }]);
  assert.equal(await store.read('anthropic'), undefined);
  assert.equal(await readFile(join(directory, 'auth.json'), 'utf8'), bytes);
  assert.deepEqual(await readdir(directory), ['auth.json']);
}));
test('refresh and logout callbacks cannot mutate the shared Codex session', async () => fixture(async directory => {
  await writeFile(join(directory, 'auth.json'), auth());
  const store: CredentialStore = new CodexSessionReference(directory, () => now);
  let invoked = false;
  await assert.rejects(store.modify('openai-codex', async () => { invoked = true; return undefined; }), /read-only/);
  await assert.rejects(store.delete('openai-codex'), /read-only/);
  assert.equal(invoked, false); assert.equal(await readFile(join(directory, 'auth.json'), 'utf8'), auth());
}));
test('expired and near-expiry access tokens require Codex-owned refresh', async () => fixture(async directory => {
  for (const seconds of [-1, 0, 299, 300]) {
    await writeFile(join(directory, 'auth.json'), auth(accessToken(now / 1000 + seconds)));
    await assert.rejects(new CodexSessionReference(directory, () => now).read('openai-codex'), /needs refreshing/);
  }
}));
test('missing, unsupported, malformed and cancelled credentials expose no source text', async () => fixture(async directory => {
  const store = new CodexSessionReference(directory, () => now);
  assert.equal(await store.read('openai-codex'), undefined);
  await writeFile(join(directory, 'auth.json'), '{private-sentinel');
  await assert.rejects(store.read('openai-codex'), error => error instanceof Error && !error.message.includes('private-sentinel'));
  await writeFile(join(directory, 'auth.json'), JSON.stringify({ auth_mode: 'apikey', OPENAI_API_KEY: 'not-this-provider' }));
  assert.equal(await store.read('openai-codex'), undefined);
  const controller = new AbortController(); controller.abort();
  await assert.rejects(store.read('openai-codex', { signal: controller.signal }));
}));
test('runtime falls back to existing Codex auth without creating a Pi credential file', async () => fixture(async directory => {
  const codex = join(directory, 'codex'); await mkdir(codex);
  const bytes = auth(accessToken(Date.now() / 1000 + 3600)); await writeFile(join(codex, 'auth.json'), bytes);
  const pi = join(directory, 'pi-not-created');
  const { runtime, source } = await createWorkerRuntime({ piAgentDir: pi, codexHome: codex });
  assert.equal(source, 'codex'); assert.equal(runtime.hasConfiguredAuth('openai-codex'), true);
  assert.ok(runtime.getModel('openai-codex', 'gpt-6.1-terra'));
  await assert.rejects(readFile(join(pi, 'auth.json')), { code: 'ENOENT' });
  assert.equal(await readFile(join(codex, 'auth.json'), 'utf8'), bytes);
}));
