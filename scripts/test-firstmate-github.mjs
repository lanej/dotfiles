import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import test from 'node:test';
import { run } from '../firstmate/github-feedback.mjs';

const ROOT = fileURLToPath(new URL('../', import.meta.url));
const delay = ms => new Promise(accept => setTimeout(accept, ms));
async function until(predicate, description) {
  const end = Date.now() + 45000;
  while (Date.now() < end) { if (await predicate()) return; await delay(100); }
  throw new Error(`Timed out: ${description}`);
}
async function json(path) { return JSON.parse(await fs.readFile(path, 'utf8')); }
async function write(path, value) { await fs.mkdir(resolve(path, '..'), { recursive: true }); await fs.writeFile(path, value); }
const logger = { child() { return this; }, debug() {}, info() {}, warn() {}, error() {}, trace() {} };

test('Paseo resumes Firstmate and its Pi owner, catches up GitHub review, and records one verified revision', { timeout: 120000 }, async () => {
  const runtime = process.env.FIRSTMATE_TEST_RUNTIME;
  const source = process.env.FIRSTMATE_SOURCE;
  assert.ok(runtime && source, 'Set FIRSTMATE_TEST_RUNTIME (Pi 1.4.0, Paseo 0.14.0, tasks-axi 0.2.6) and FIRSTMATE_SOURCE');
  const modules = join(resolve(runtime), 'node_modules');
  assert.equal((await json(join(modules, '@earendil-works/pi-coding-agent/package.json'))).version, '1.4.0');
  assert.equal((await json(join(modules, '@getpaseo/server/package.json'))).version, '0.14.0');
  const { PiCliRuntime } = await import(pathToFileURL(join(modules, '@getpaseo/server/dist/server/server/agent/providers/pi/cli-runtime.js')));
  const { ProviderOverridesSchema } = await import(pathToFileURL(join(modules, '@getpaseo/protocol/dist/provider-config.js')));
  const directory = await fs.mkdtemp(join(tmpdir(), 'firstmate-github-'));
  const childEnv = { ...process.env }; delete childEnv.NODE_TEST_CONTEXT;
  const testContext = process.env.NODE_TEST_CONTEXT; delete process.env.NODE_TEST_CONTEXT;
  const home = join(directory, 'home'), fleet = join(home, 'src/firstmate'), worktree = join(directory, 'worktree');
  const issue = 'https://github.com/lanej/fixture/issues/7', pr = 'https://github.com/lanej/fixture/pull/8';
  const errors = [], requests = [], comments = [], inline = [], reviews = [], posted = [], modelRequests = [];
  const remote = join(directory, 'origin.git');
  let task, originalHead;
  const remoteHead = branch => execFileSync('git', ['--git-dir', remote, 'rev-parse', `refs/heads/${branch}`], { encoding: 'utf8' }).trim();
  let main, worker, origin;
  const server = createServer(async (request, response) => {
    try {
      let body = ''; for await (const chunk of request) body += chunk;
      const url = new URL(request.url, origin);
      if (url.pathname === '/v1/chat/completions') {
        const payload = JSON.parse(body); modelRequests.push(payload);
        assert.ok(modelRequests.length < 50, 'Model fixture did not converge');
        const messageText = message => typeof message.content === 'string' ? message.content
          : (message.content ?? []).filter(block => block.type === 'text').map(block => block.text).join('\n');
        const index = payload.messages.findLastIndex(message => messageText(message).includes('GitHub feedback for your assigned task'));
        let delta = { content: 'Work recorded; awaiting the next task event.' };
        if (payload.model === 'worker' && index >= 0) {
          const event = JSON.parse(messageText(payload.messages[index]).split('\n\n').at(-1));
          const outputs = payload.messages.slice(index + 1).filter(message => message.role === 'tool');
          const call = (name, args) => ({ tool_calls: [{ index: 0, id: `fixture-${modelRequests.length}`, type: 'function',
            function: { name, arguments: JSON.stringify(args) } }] });
          if (event.type === 'inline') {
            assert.equal(event.authority, 'owner-direction', 'Human feedback shares the agent’s GitHub login');
            if (outputs.length === 0) delta = call('read', { path: 'price.mjs' });
            else if (outputs.length === 1) delta = call('edit', { path: 'price.mjs', oldText: 'amount - fee', newText: 'amount + fee' });
            else if (outputs.length === 2) delta = call('bash', { command: 'node --test' });
            else if (outputs.length === 3) {
              assert.match(JSON.stringify(outputs.at(-1)), /pass 1/, `The real regression must pass before replying: ${JSON.stringify(outputs.at(-1))}`);
              delta = call('bash', { command: 'git add price.mjs' });
            } else if (outputs.length === 4) delta = call('bash', { command: "git commit -m 'fix: add fee'" });
            else if (outputs.length === 5) delta = call('bash', { command: 'git push origin HEAD' });
            else if (outputs.length === 6) {
              delta = call('firstmate_github_reply', { eventId: event.id, body: 'Fixed the fee calculation. node --test passes; ready for another review.' });
            } else if (outputs.length === 7) delta = call('firstmate_github_done', { eventId: event.id, summary: `${pr} revised and verified`, needsFirstmate: false });
          } else if (outputs.length === 0) delta = call('firstmate_github_done', { eventId: event.id, summary: `${event.url} discussion/check state reviewed`, needsFirstmate: false });
        }
        response.writeHead(200, { 'Content-Type': 'text/event-stream' });
        for (const [part, reason] of [[{ role: 'assistant', ...delta }, null], [{}, delta.tool_calls ? 'tool_calls' : 'stop']]) {
          response.write('data: ' + JSON.stringify({ id: 'fixture', object: 'chat.completion.chunk', created: 0,
            model: payload.model, choices: [{ index: 0, delta: part, finish_reason: reason }] }) + '\n\n');
        }
        response.end('data: [DONE]\n\n'); return;
      }
      requests.push([request.method, url.pathname]);
      assert.equal(request.headers.authorization, 'Bearer fixture-token');
      let output;
      if (url.pathname === '/user') output = { login: 'lanej' };
      else if (url.pathname === '/graphql' && request.method === 'POST') {
        assert.match(JSON.parse(body).query, /^query\(/);
        output = { data: { repository: { pullRequest: { reviewThreads: { nodes: inline.filter(comment => !comment.in_reply_to_id).map(comment => ({
          id: `thread-${comment.id}`, isResolved: false, comments: { nodes: [{ databaseId: comment.id }] },
        })), pageInfo: { hasNextPage: false, endCursor: null } } } } } };
      }
      else if (url.pathname === '/repos/lanej/fixture/issues/7') output = { title: 'Correct the fee calculation', state: 'open', labels: [] };
      else if (url.pathname === '/repos/lanej/fixture/issues/7/comments') output = comments;
      else if (url.pathname === '/repos/lanej/fixture/pulls/8') output = { state: 'open', head: { sha: remoteHead('fix-fee') }, labels: [], merged: false, draft: false, mergeable: true };
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/reviews') output = reviews;
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/comments') output = inline;
      else if (url.pathname === '/repos/lanej/fixture/issues/8/comments') output = posted;
      else if (/\/commits\/.*\/check-runs$/.test(url.pathname)) output = { check_runs: [{ id: 1, name: 'tests', status: 'completed', conclusion: 'success' }] };
      else if (/\/commits\/.*\/statuses$/.test(url.pathname)) output = [];
      else if (url.pathname === '/repos/lanej/fixture/pulls/8/comments/12/replies' && request.method === 'POST') {
        output = { id: 100, body: JSON.parse(body).body, user: { login: 'lanej' }, html_url: `${pr}#discussion_r100`, updated_at: '2026-11-02T01:03:00Z', in_reply_to_id: 12 };
        inline.push(output); posted.push(output);
      } else throw new Error(`Unexpected GitHub mutation or endpoint: ${request.method} ${url.pathname}`);
      const encoded = JSON.stringify(output), etag = '"' + createHash('sha256').update(encoded).digest('hex') + '"';
      if (request.method === 'GET' && request.headers['if-none-match'] === etag) {
        response.writeHead(304, { ETag: etag }); response.end();
      } else {
        response.writeHead(200, { 'Content-Type': 'application/json', ETag: etag }); response.end(encoded);
      }
    } catch (error) { errors.push(error.stack); response.writeHead(500); response.end(JSON.stringify({ error: error.message })); }
  });
  try {
    await new Promise(accept => server.listen(0, '127.0.0.1', accept));
    origin = `http://127.0.0.1:${server.address().port}`;
    await fs.mkdir(join(fleet, 'state'), { recursive: true });
    await fs.mkdir(join(fleet, 'data'), { recursive: true });
    await fs.mkdir(join(fleet, 'config'), { recursive: true });
    await fs.mkdir(worktree);
    await fs.symlink(join(resolve(source), 'bin'), join(fleet, 'bin'));
    await fs.symlink(join(resolve(source), '.tasks.toml'), join(fleet, '.tasks.toml'));
    // Native Firstmate dispatch/supervision is exercised by its existing detector.
    // Here task metadata is seeded; ambient primary extensions are deliberately disabled.
    for (const name of ['fm-primary-pi-watch', 'fm-primary-turnend-guard', 'fm-branch-supervision']) {
      await write(join(fleet, '.pi/extensions', `${name}.ts`), 'export default function () {}\n');
    }
    await write(join(fleet, 'data/backlog.md'), '# Backlog\n\n## In flight\n\n## Queued\n\n## Done\n');
    await write(join(worktree, 'price.mjs'), 'export const total = (amount, fee) => amount - fee;\n');
    await write(join(worktree, 'price.test.mjs'), "import {test} from 'node:test';import assert from 'node:assert/strict';import {total} from './price.mjs';test('adds fee',()=>assert.equal(total(100,5),105));\n");
    const git = (...args) => execFileSync('git', ['-C', worktree, ...args], { encoding: 'utf8' }).trim();
    git('init', '-q', '-b', 'main'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid');
    git('add', '.'); git('commit', '-qm', 'fixture');
    const head = git('rev-parse', 'HEAD');
    originalHead = head;
    execFileSync('git', ['init', '--bare', '-q', remote]);
    git('remote', 'add', 'origin', remote); git('push', '-q', 'origin', 'main');
    git('switch', '-qc', 'fix-fee'); git('push', '-q', 'origin', 'fix-fee');
    assert.throws(() => execFileSync('node', ['--test'], { cwd: worktree, env: childEnv, stdio: 'pipe' }), 'The actual fee regression starts red');
    const env = { ...childEnv, HOME: home, FIRSTMATE_HOME: fleet, FIRSTMATE_SOURCE: resolve(source), GH_TOKEN: 'fixture-token',
      PATH: `${join(modules, '.bin')}:${process.env.PATH}`, PI_CODING_AGENT_DIR: join(home, '.pi/agent'), PI_SKIP_VERSION_CHECK: '1', PI_TELEMETRY: '0' };
    delete env.FM_TASK_ID; delete env.FM_TASK_INBOX; delete env.FM_HOME; delete env.GITHUB_TOKEN;
    await write(join(fleet, 'config/crew-harness'), 'pi\n');
    await write(join(home, '.pi/agent/settings.json'), JSON.stringify({ theme: 'dark', extensions: [] }));
    await write(join(home, '.paseo/config.json'), JSON.stringify({ listen: '127.0.0.1:6767', agents: { providers: { codex: { enabled: true } } } }));
    execFileSync('make', ['firstmate-mobile-config', `FIRSTMATE_HOME=${fleet}`], { cwd: ROOT, env, stdio: 'pipe' });
    await write(join(fleet, 'config/github-feedback.json'), JSON.stringify({ owner: 'lanej', pollSeconds: 10 }));
    execFileSync('make', ['firstmate-mobile-config', `FIRSTMATE_HOME=${fleet}`], { cwd: ROOT, env, stdio: 'pipe' });
    assert.equal((await json(join(home, '.pi/agent/settings.json'))).theme, 'dark');
    assert.equal((await json(join(fleet, 'config/github-feedback.json'))).pollSeconds, 10);
    assert.equal(await fs.readFile(join(fleet, 'config/crew-harness'), 'utf8'), 'pi\n');
    const paseoConfig = await json(join(home, '.paseo/config.json'));
    ProviderOverridesSchema.parse(paseoConfig.agents.providers);
    assert.equal(paseoConfig.agents.providers.codex.enabled, true);
    assert.equal(paseoConfig.agents.providers.firstmate.extends, 'pi');
    await write(join(home, '.pi/agent/models.json'), JSON.stringify({ providers: { fixture: { baseUrl: `${origin}/v1`, apiKey: 'fixture', api: 'openai-completions',
      models: ['primary', 'worker'].map(id => ({ id, name: id, reasoning: false, input: ['text'], contextWindow: 128000, maxTokens: 2048,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 } })) } } }));
    const fixture = join(directory, 'fixture.mjs');
    await write(fixture, `import {writeFileSync} from 'node:fs'; const original = globalThis.fetch; globalThis.fetch = (url, opts) => original(String(url).startsWith('https://api.github.com/') ? ${JSON.stringify(origin)} + String(url).slice('https://api.github.com'.length) : url, opts); export default function (pi) { pi.on('session_start', () => { if (!process.env.FM_TASK_ID) writeFileSync(${JSON.stringify(join(fleet, 'state/.lock'))}, String(process.pid)); }); }\n`);
    const intakeEnv = { ...env, NODE_OPTIONS: `--import ${fixture}` };
    const queued = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['github', 'intake', issue], { env: intakeEnv }));
    task = queued.id;
    assert.ok(task, 'GitHub issue queued in the native Firstmate backlog');
    const repeated = JSON.parse(await run(join(ROOT, 'bin/firstmate'), ['github', 'intake', issue], { env: intakeEnv }));
    assert.equal(repeated.id, task, 'Repeated intake preserves task identity');
    await run(join(resolve(source), 'bin/fm-contributions.sh'), ['enroll', task, pr], { env: { ...env, FM_HOME: fleet } });
    await write(join(fleet, 'state', `${task}.meta`), `harness=pi\nkind=ship\nworktree=${worktree}\nproject=${worktree}\nbranch=fix-fee\nspawn_gen=fixture-generation\nbackend=tmux\nwindow=fixture:1\n`);
    await write(join(fleet, 'state', `${task}.status`), 'working: awaiting review\n');
    const launch = async (model, session, task) => {
      const rpc = new PiCliRuntime({ logger, command: task ? [join(modules, '.bin/pi')] : paseoConfig.agents.providers.firstmate.command });
      return rpc.startSession({ cwd: task ? worktree : fleet, model: `fixture/${model}`, session,
        env: { ...env, ...(task ? { FM_TASK_ID: queued.id, FM_TASK_INBOX: join(fleet, 'state', `${queued.id}.inbox`) } : {}) },
        extraArgs: [...(task ? [] : ['--no-extensions']), '--extension', fixture] });
    };
    worker = await launch('worker', undefined, true);
    await worker.prompt('Continue the assigned fee task and wait for GitHub review.');
    await until(async () => (await fs.stat(join(fleet, 'data', task, 'github-session.json')).catch(() => null)), 'Pi owner registered');
    main = await launch('primary'); await main.prompt('Track the assigned fee task; keep this conversation available for steering.');
    await until(async () => requests.some(([, path]) => path.endsWith('/pulls/8')), 'Primary observes tracked GitHub objects');
    await until(async () => !(await worker.getState()).isStreaming, 'Initial worker event settles');
    const primaryState = await main.getState(), workerState = await worker.getState();
    assert.ok(primaryState.sessionFile && workerState.sessionFile);
    await worker.close(); worker = undefined; await main.close(); main = undefined;
    inline.push({ id: 12, body: 'The fee should be added, not subtracted. Please fix this and run the regression.', user: { login: 'lanej' },
      html_url: `${pr}#discussion_r12`, updated_at: '2026-11-02T01:02:00Z', commit_id: originalHead, path: 'price.mjs', line: 1 });
    comments.push({ id: 13, body: 'Keep this scoped to the fee calculation.', user: { login: 'lanej' }, html_url: `${issue}#issuecomment-13`, updated_at: '2026-11-02T01:02:01Z' });
    reviews.push({ id: 14, state: 'CHANGES_REQUESTED', body: '', user: { login: 'lanej' }, html_url: `${pr}#pullrequestreview-14`, submitted_at: '2026-11-02T01:02:00Z', commit_id: originalHead });
    main = await launch('primary', primaryState.sessionFile);
    await until(async () => (await main.getMessages()).some(message => JSON.stringify(message).includes('Firstmate recovery')), 'Unavailable owner escalates');
    worker = await launch('worker', workerState.sessionFile, true);
    await until(() => posted.length === 1, 'Recovered Pi owner revises and replies inline');
    await until(async () => (await fs.readFile(join(fleet, 'state', `${task}.status`), 'utf8')).includes('revised and verified'), 'Outcome reaches Firstmate task record');
    assert.equal((await worker.getState()).sessionId, workerState.sessionId, 'Recovered the recorded worker session');
    assert.equal((await main.getState()).sessionId, primaryState.sessionId, 'Recovered the existing Paseo primary');
    assert.match(execFileSync('node', ['--test'], { cwd: worktree, env: childEnv, encoding: 'utf8' }), /pass 1/);
    assert.match(posted[0].html_url, /discussion_r100/);
    assert.notEqual(remoteHead('fix-fee'), head, 'Worker published the revised task branch');
    assert.equal(remoteHead('main'), head, 'Delivery into the default branch remains unauthorized');
    await until(async () => (await fs.readdir(join(fleet, 'state', `${task}.inbox`))).filter(name => name.endsWith('.msg')).length === 0, 'Feedback acknowledged through native inbox');
    reviews.push({ id: 15, state: 'APPROVED', body: '', user: { login: 'lanej' }, html_url: `${pr}#pullrequestreview-15`, submitted_at: '2026-11-02T01:04:00Z', commit_id: remoteHead('fix-fee') });
    // Allow a full poll after the agent's own GitHub reply: no acknowledgment loop.
    await delay(11000);
    assert.equal(posted.length, 1);
    assert.equal(remoteHead('main'), head, 'Review approval does not authorize merging');
    assert.equal(requests.some(([method]) => !['GET', 'POST'].includes(method)), false, 'No merge API mutation');
    assert.deepEqual(errors, []);
    assert.ok(modelRequests.some(payload => payload.model === 'worker'));
  } finally {
    await worker?.close(); await main?.close();
    server.closeAllConnections(); await new Promise(accept => server.close(accept));
    await fs.rm(directory, { recursive: true, force: true });
    if (errors.length) console.error(errors.join('\n'));
    if (testContext !== undefined) process.env.NODE_TEST_CONTEXT = testContext;
  }
});
