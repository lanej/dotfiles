#!/usr/bin/env node
// One workflow through the real dispatcher and reviewer, using Pi's real RpcClient.
// --native also runs the real Pi CLI against a local HTTP fixture model.
import assert from 'node:assert/strict';
import { execFile, execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir } from 'node:os';
import { delimiter, dirname, join, resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const FILE = fileURLToPath(import.meta.url);
const NATIVE = process.argv.includes('--native');
const REVIEW = { verdict: 'changes_requested', review: '## Code Review Summary\n'
  + 'price.js subtracts the fee. The total must add it. Verification was not run.\n'
  + 'Read-only evidence: \u2028fee\u2029.' };
const BROKEN_SOURCE = 'export const total = (amount, fee) => amount - fee;\n';

function installedPi() {
  const executable = (process.env.PATH ?? '').split(delimiter).map(path => join(path, 'pi'))
    .find(path => existsSync(path));
  assert.ok(executable, 'Install @earendil-works/pi-coding-agent@1.4.0 before running this check');
  const cli = realpathSync(executable);
  for (let directory = dirname(cli); ; directory = dirname(directory)) {
    const path = join(directory, 'package.json');
    if (existsSync(path)) {
      const metadata = JSON.parse(readFileSync(path, 'utf8'));
      if (metadata.name === '@earendil-works/pi-coding-agent') {
        assert.equal(metadata.version, '1.4.0');
        return { cli, sdkUrl: pathToFileURL(resolve(directory, metadata.exports['.'].import)).href };
      }
    }
    if (dirname(directory) === directory) throw new Error('Cannot find Pi package for ' + cli);
  }
}

async function fakePi() {
  if (process.argv.includes('--version')) { console.log('1.4.0'); return; }
  const option = name => process.argv[process.argv.indexOf(name) + 1];
  assert.deepEqual(option('--tools').split(',').sort(), ['find', 'grep', 'ls', 'read']);
  for (const flag of ['--no-extensions', '--no-mcp', '--no-skills', '--no-prompt-templates',
    '--no-context-files', '--no-approve']) assert.ok(process.argv.includes(flag));
  assert.ok(readFileSync(option('--append-system-prompt'), 'utf8').includes('PHA-P03'));
  const sessionId = option('--session-id');
  const sessionFile = join(option('--session-dir'), sessionId + '.jsonl');
  mkdirSync(dirname(sessionFile), { recursive: true });
  writeFileSync(sessionFile, '{"type":"session"}\n');
  const emit = event => process.stdout.write(JSON.stringify(event) + '\n');
  let buffer = '';
  process.stdin.setEncoding('utf8');
  for await (const chunk of process.stdin) {
    buffer += chunk;
    let newline;
    while ((newline = buffer.indexOf('\n')) !== -1) {
      const request = JSON.parse(buffer.slice(0, newline));
      buffer = buffer.slice(newline + 1);
      if (request.type === 'get_state') {
        emit({ type: 'response', id: request.id, success: true, data: {
          sessionId, sessionFile, model: { provider: 'review-fixture', id: 'tiny' },
        } });
      } else if (request.type === 'prompt') {
        assert.ok(request.message.includes('amount - fee'));
        emit({ type: 'response', id: request.id, success: true, data: { disposition: 'started' } });
        emit({ type: 'message_end', message: { role: 'assistant', stopReason: 'error', content: [] } });
        emit({ type: 'agent_end', willRetry: true });
        await delay(20);
        emit({ type: 'tool_execution_start', toolName: 'read' });
        assert.equal(readFileSync('price.js', 'utf8'), BROKEN_SOURCE);
        emit({ type: 'message_end', message: { role: 'assistant', stopReason: 'stop',
          content: [{ type: 'text', text: JSON.stringify(REVIEW) }] } });
        emit({ type: 'agent_end', willRetry: false });
        emit({ type: 'agent_settled', aborted: false });
      } else if (request.type === 'abort') {
        emit({ type: 'response', id: request.id, success: true });
      }
    }
  }
}

function fixtureModel() {
  const requests = [], failures = [];
  const server = createServer(async (request, response) => {
    let data = '';
    for await (const chunk of request) data += chunk;
    const payload = JSON.parse(data);
    requests.push(payload);
    const tools = payload.tools?.map(tool => tool.function.name).sort();
    if (JSON.stringify(tools) !== JSON.stringify(['find', 'grep', 'ls', 'read'])) {
      failures.push('Unexpected exposed tools: ' + JSON.stringify(tools));
    }
    const serialized = JSON.stringify(payload.messages);
    if (!serialized.includes('PHA-P03') || !serialized.toLowerCase().includes('code review')) {
      failures.push('Shared reviewer/Builder instructions missing');
    }
    if (requests.length === 1) {
      response.writeHead(503, { 'Content-Type': 'application/json' });
      response.end('{"error":{"message":"fixture retry","type":"server_error"}}');
      return;
    }
    let delta, finish;
    if (payload.messages.some(message => message.role === 'tool')) {
      if (!serialized.includes('amount - fee')) failures.push('Reviewed source never reached the model');
      delta = { content: JSON.stringify(REVIEW) };
      finish = 'stop';
    } else {
      delta = { tool_calls: [{ index: 0, id: 'review-read', type: 'function',
        function: { name: 'read', arguments: '{"path":"price.js"}' } }] };
      finish = 'tool_calls';
    }
    response.writeHead(200, { 'Content-Type': 'text/event-stream' });
    for (const [part, reason] of [[{ role: 'assistant', ...delta }, null], [{}, finish]]) {
      const chunk = { id: 'fixture', object: 'chat.completion.chunk', created: 0, model: 'tiny',
        choices: [{ index: 0, delta: part, finish_reason: reason }] };
      response.write('data: ' + JSON.stringify(chunk) + '\n\n');
    }
    response.end('data: [DONE]\n\n');
  });
  return { server, requests, failures };
}

if (process.argv.includes('--fixture-pi')) {
  await fakePi();
} else {
  test('dispatcher review preserves the checkout and leaves finish with the caller', { timeout: 55000 }, async () => {
    const directory = mkdtempSync(join(tmpdir(), 'pi-review-'));
    const repo = join(directory, 'repo');
    mkdirSync(repo);
    const git = (...args) => execFileSync('git', ['-C', repo, ...args], { encoding: 'utf8' }).trim();
    const { server, requests, failures } = fixtureModel();
    try {
      git('init', '-q');
      git('config', 'user.name', 'Review Fixture');
      git('config', 'user.email', 'review@example.invalid');
      writeFileSync(join(repo, 'price.js'), 'export const total = (amount, fee) => amount + fee;\n');
      mkdirSync(join(repo, '.pi/extensions'), { recursive: true });
      const marker = join(directory, 'extension-executed');
      writeFileSync(join(repo, '.pi/extensions/unwanted.ts'),
        "import {writeFileSync} from 'node:fs';\nexport default function () {"
        + 'writeFileSync(' + JSON.stringify(marker) + ", 'unexpected');}\n");
      git('add', '.');
      git('commit', '-qm', 'Base');
      git('update-ref', 'refs/remotes/origin/main', 'HEAD');
      writeFileSync(join(repo, 'price.js'), BROKEN_SOURCE);
      git('add', '.');
      git('commit', '-qm', 'Introduce fee regression');
      const head = git('rev-parse', 'HEAD');

      const taskHome = join(directory, 'home');
      const state = join(taskHome, '.local/state/dispatcher/repo');
      mkdirSync(state, { recursive: true });
      writeFileSync(join(state, 'builder1.json'), JSON.stringify({ repo, slug: 'review' }));
      const config = join(directory, 'dispatcher.json');
      writeFileSync(config, '{"targetBranch":"main"}');
      const executables = join(directory, 'bin');
      mkdirSync(executables);
      writeFileSync(join(executables, 'claude'), '#!/usr/bin/env node\nconsole.log('
        + JSON.stringify(JSON.stringify([{ id: 'builder1', cwd: repo }])) + ');\n', { mode: 0o755 });
      const env = { ...process.env, HOME: taskHome, PATH: executables + delimiter + process.env.PATH,
        DISPATCHER_CONFIG: config, DISPATCHER_PI_REVIEW: join(ROOT, 'bin/pi-review'),
        PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' };
      const installed = installedPi();
      let pi = installed.cli;
      if (NATIVE) {
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const agentDirectory = join(directory, 'pi-agent');
        mkdirSync(agentDirectory);
        writeFileSync(join(agentDirectory, 'models.json'), JSON.stringify({ providers: {
          'review-fixture': { baseUrl: 'http://127.0.0.1:' + server.address().port + '/v1',
            api: 'openai-completions', apiKey: 'fixture', models: [{ id: 'tiny' }] },
        } }));
        env.PI_CODING_AGENT_DIR = agentDirectory;
      } else {
        // Simulate only the CLI; retain the installed, maintained RpcClient.
        const fixture = join(directory, 'pi-fixture');
        mkdirSync(fixture);
        writeFileSync(join(fixture, 'package.json'), JSON.stringify({
          name: '@earendil-works/pi-coding-agent', version: '1.4.0', type: 'module',
          exports: { '.': { import: './index.mjs' } },
        }));
        writeFileSync(join(fixture, 'index.mjs'), 'export { RpcClient } from ' + JSON.stringify(installed.sdkUrl) + ';\n');
        pi = join(fixture, 'cli.mjs');
        writeFileSync(pi, '#!/usr/bin/env node\nprocess.argv.push("--fixture-pi");\nawait import('
          + JSON.stringify(pathToFileURL(FILE).href) + ');\n', { mode: 0o755 });
      }
      const output = join(directory, 'review-result');
      let result;
      try {
        result = await promisify(execFile)('bash', [
          join(ROOT, 'ai/skills/dispatcher/scripts/dispatcher-worker'), 'review-pi', 'builder1',
          '--model', 'review-fixture/tiny', '--timeout', '12', '--pi-bin', pi, '--output-dir', output,
        ], { cwd: repo, env, encoding: 'utf8', timeout: 50000 });
      } catch (error) {
        assert.fail((error.stdout ?? '') + (error.stderr ?? '')
          + (existsSync(join(output, 'stderr.log')) ? readFileSync(join(output, 'stderr.log'), 'utf8') : error.message));
      }
      const record = JSON.parse(result.stdout);
      assert.equal(record.status, 'reviewed');
      assert.equal(record.verdict, 'changes_requested');
      assert.equal(record.cwd, realpathSync(repo));
      assert.equal(record.head, head);
      assert.deepEqual(record.model, { provider: 'review-fixture', id: 'tiny' });
      assert.ok(existsSync(record.sessionFile));
      assert.equal(readFileSync(join(output, 'review.md'), 'utf8').trim(), REVIEW.review);
      assert.deepEqual(JSON.parse(readFileSync(join(output, 'result.json'), 'utf8')), record);
      assert.equal(existsSync(marker), false, 'Project extension ran during a restricted review');
      assert.equal(git('rev-parse', 'HEAD'), head);
      assert.equal(git('status', '--porcelain'), '');
      assert.ok(existsSync(join(state, 'builder1.json')), 'Review consumed the builder state');
      if (NATIVE) {
        assert.deepEqual(failures, []);
        assert.ok(requests.length >= 3);
      }
    } finally {
      if (server.listening) await new Promise(resolve => server.close(resolve));
      rmSync(directory, { recursive: true, force: true });
    }
  });
}
