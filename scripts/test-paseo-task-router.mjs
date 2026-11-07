import assert from 'node:assert/strict';
import { spawn, execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'node:net';
import { setTimeout as delay } from 'node:timers/promises';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const binary = process.env.PASEO_TASK_ROUTER_BIN;
assert.ok(binary, 'Build the reviewed standalone router and set PASEO_TASK_ROUTER_BIN');
const routerConfig = process.env.PASEO_TASK_ROUTER_CONFIG;
assert.ok(routerConfig, 'Set PASEO_TASK_ROUTER_CONFIG to the standalone router config.json');
const directory = await mkdtemp(join(tmpdir(), 'paseo-task-router-'));
let router;
try {
  const listener = createServer();
  await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
  const port = listener.address().port;
  await new Promise(resolve => listener.close(resolve));
  const config = JSON.parse(await readFile(routerConfig, 'utf8'));
  config.port = port;
  const configPath = join(directory, 'config.json');
  await writeFile(configPath, JSON.stringify(config));
  router = spawn(binary, ['--config', configPath, '--state-file', join(directory, 'sessions.sqlite')], { stdio: 'ignore' });
  for (let count = 0; count < 100; count++) {
    if (router.exitCode !== null) throw new Error('Temporary router failed to start');
    if (await fetch(`http://127.0.0.1:${port}/healthz`).then(response => response.ok).catch(() => false)) break;
    if (count === 99) throw new Error('Temporary router did not become ready');
    await delay(50);
  }
  const agentDir = join(directory, 'pi');
  await mkdir(agentDir);
  const models = JSON.parse(await readFile(join(root, 'pi/paseo-tasks.models.json'), 'utf8'));
  models.providers['bedrock-sonnet-router'].baseUrl = `http://127.0.0.1:${port}/anthropic`;
  await writeFile(join(agentDir, 'models.json'), JSON.stringify(models));
  await writeFile(join(agentDir, 'settings.json'), JSON.stringify({ defaultThinkingLevel: 'medium' }));
  const trace = join(directory, 'request.json');
  const extension = join(directory, 'probe.mjs');
  await writeFile(extension, `import { writeFileSync } from 'node:fs';
export default pi => {
  pi.on('before_provider_request', event => {
    event.payload.max_tokens = 256;
    const { model, thinking, output_config } = event.payload;
    writeFileSync(${JSON.stringify(trace)}, JSON.stringify({ model, thinking, output_config }));
  });
};`);
  const invocation = promisify(execFile)(join(root, 'bin/paseo-pi'), [
    '--mode', 'json', '--print', '--no-session', '--provider', 'bedrock-sonnet-router',
    '--model', 'us.anthropic.claude-sonnet-5-5', '--thinking', 'medium', '--no-tools',
    '--offline', '--no-mcp', '--no-context-files', '--no-approve',
    '--no-extensions', '--extension', join(root, 'pi/extensions/paseo-router.mjs'), '--extension', extension,
    '--no-skills', '--no-prompt-templates', '--no-themes', 'Reply exactly TASK_ROUTER_OK.',
  ], { cwd: directory, timeout: 90000, maxBuffer: 4 * 1024 * 1024,
    env: { ...process.env, PI_CODING_AGENT_DIR: agentDir, PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' } });
  // WHY: Print mode reads piped stdin through EOF before processing its prompt.
  invocation.child.stdin.end();
  const result = await invocation;
  const events = result.stdout.trim().split('\n').map(line => JSON.parse(line));
  const assistant = events.filter(event => event.type === 'message_end' && event.message?.role === 'assistant').at(-1)?.message;
  assert.ok(assistant, 'Pi returned a completed assistant message');
  assert.equal(assistant.stopReason, 'stop');
  assert.equal(assistant.provider, 'bedrock-sonnet-router');
  assert.equal(assistant.model, 'us.anthropic.claude-sonnet-5-5');
  assert.equal(assistant.content.filter(item => item.type === 'text').map(item => item.text).join('').trim(), 'TASK_ROUTER_OK');
  const request = JSON.parse(await readFile(trace, 'utf8'));
  assert.equal(request.model, 'us.anthropic.claude-sonnet-5-5');
  assert.equal(request.thinking?.type, 'adaptive');
  assert.equal(request.output_config?.effort, 'medium');
  const health = await fetch(`http://127.0.0.1:${port}/healthz`).then(response => response.json());
  assert.equal(health.pinned_sessions, 1);
  assert.equal(health.failures, 0);
  assert.equal(health.incomplete_streams, 0);
  console.log(JSON.stringify({ liveSonnetReply: true, provider: 'bedrock-sonnet-router', thinking: request,
    sessionAffinity: true, preservedExistingCredentials: true }));
} finally {
  if (router && router.exitCode === null) {
    const closed = new Promise(resolve => router.once('exit', resolve));
    router.kill('SIGTERM');
    await Promise.race([closed, delay(5000)]);
    if (router.exitCode === null) { router.kill('SIGKILL'); await closed; }
  }
  await rm(directory, { recursive: true, force: true });
}
