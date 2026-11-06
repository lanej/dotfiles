import { spawn } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import * as fs from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const native = join(root, 'scripts/firstmate-feedback-native.sh');
export const prefix = 'FIRSTMATE_GITHUB_EVENT v1\n';
const digest = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
const taskPattern = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
export const taskId = value => {
  if (!taskPattern.test(value ?? '')) throw new Error('Invalid Firstmate task ID');
  return value;
};
export async function readJSON(path, fallback) {
  try { return JSON.parse(await fs.readFile(path, 'utf8')); }
  catch (error) {
    if (error.code === 'ENOENT' && fallback !== undefined) return fallback;
    if (error instanceof SyntaxError) throw new Error(`Invalid JSON in ${path}; preserve and repair the existing file`);
    throw error;
  }
}
export async function atomicJSON(path, value) {
  await fs.mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const temporary = `${path}.${randomUUID()}.tmp`;
  try {
    await fs.writeFile(temporary, JSON.stringify(value, null, 2) + '\n', { mode: 0o600, flag: 'wx' });
    await fs.rename(temporary, path);
  } finally { await fs.rm(temporary, { force: true }); }
}
export function run(command, args, { input, env = process.env, signal, timeout = 30000 } = {}) {
  return new Promise((accept, reject) => {
    const child = spawn(command, args, { env, signal, stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '', stderr = '', oversized = false;
    const timer = setTimeout(() => child.kill('SIGKILL'), timeout);
    child.stdout.on('data', chunk => { stdout += chunk; if (stdout.length > 16 * 1024 * 1024) { oversized = true; child.kill('SIGKILL'); } });
    child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-4000); });
    child.on('error', error => { clearTimeout(timer); reject(error); });
    child.on('close', code => {
      clearTimeout(timer);
      if (code === 0 && !oversized) accept(stdout.trim());
      else reject(new Error(`${command} failed (${code ?? 'terminated'}): ${stderr || (args[0] === native ? stdout.slice(-2000) : '')}`));
    });
    child.stdin.on('error', () => {});
    child.stdin.end(input);
  });
}
export const nativeCall = (home, action, args = [], options = {}) => run('bash', [native, home, action, ...args], options);
export async function config(home) {
  const value = await readJSON(join(home, 'config/github-feedback.json'), null);
  if (!value) return null;
  if (!/^[A-Za-z0-9-]+$/.test(value.owner ?? '') || !Number.isInteger(value.pollSeconds) || value.pollSeconds < 10 || value.pollSeconds > 3600) {
    throw new Error('github-feedback.json requires owner and pollSeconds (10..3600)');
  }
  return value;
}
export async function metadata(home, id) {
  const text = await fs.readFile(join(home, 'state', `${taskId(id)}.meta`), 'utf8');
  return Object.fromEntries(text.split('\n').filter(line => line.includes('=')).map(line => {
    const at = line.indexOf('='); return [line.slice(0, at), line.slice(at + 1)];
  }));
}
export function alive(pid) {
  if (!Number.isSafeInteger(pid) || pid <= 0) return false;
  try { process.kill(pid, 0); return true; } catch (error) { return error.code === 'EPERM'; }
}
export async function withLock(home, path, operation) {
  await fs.mkdir(dirname(path), { recursive: true, mode: 0o700 });
  // The existing Firstmate lock library owns contention and stale-process recovery.
  // EOF releases the lease even if this Node process exits unexpectedly.
  const child = spawn('bash', [native, home, 'lock', path], { stdio: ['pipe', 'pipe', 'pipe'] });
  let stderr = '';
  child.stderr.on('data', chunk => { stderr = (stderr + chunk).slice(-2000); });
  const closed = new Promise(accept => child.on('close', accept));
  await new Promise((accept, reject) => {
    child.once('error', reject);
    child.stdout.once('data', () => accept());
    child.once('close', code => reject(new Error(`Firstmate feedback lock unavailable (${code}): ${stderr}`)));
  });
  try { return await operation(); }
  finally { child.stdin.end(); await closed; }
}
async function credential() {
  const token = process.env.GH_TOKEN || process.env.GITHUB_TOKEN;
  if (token) return token;
  const result = await run('git', ['credential', 'fill'], {
    input: 'protocol=https\nhost=github.com\n\n',
    env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GCM_INTERACTIVE: 'Never' }, timeout: 10000,
  });
  const password = result.split('\n').find(line => line.startsWith('password='))?.slice(9);
  if (!password) throw new Error('GitHub authentication missing: configure a git credential or GH_TOKEN');
  return password;
}
export class GitHub {
  constructor({ base = 'https://api.github.com', token, signal } = {}) {
    this.base = base; this.token = token; this.signal = signal;
    this.cache = new Map();
  }
  async request(path, { method = 'GET', body } = {}) {
    if (!/^\/(repos\/|user$|graphql$)/.test(path)) throw new Error('Unexpected GitHub API path');
    this.token ??= await credential();
    const cached = method === 'GET' ? this.cache.get(path) : null;
    const response = await fetch(this.base + path, {
      method, headers: { Authorization: `Bearer ${this.token}`, Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': 'application/json',
        ...(cached ? { 'If-None-Match': cached.etag } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: this.signal ? AbortSignal.any([this.signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),
      redirect: 'error',
    });
    if (response.status === 304 && cached) return cached.data;
    if (!response.ok) throw new Error(`GitHub ${method} ${path}: HTTP ${response.status}`);
    const data = await response.json();
    const etag = response.headers.get('etag');
    if (method === 'GET' && etag) this.cache.set(path, { data, etag });
    return data;
  }
  async list(path, field) {
    const all = [];
    for (let page = 1; page <= 100; page++) {
      const data = await this.request(`${path}${path.includes('?') ? '&' : '?'}per_page=100&page=${page}`);
      const rows = field ? data[field] : data;
      if (!Array.isArray(rows)) throw new Error(`Unexpected GitHub list: ${path}`);
      all.push(...rows);
      if (rows.length < 100) return all;
    }
    throw new Error(`GitHub pagination bound reached: ${path}; cursor retained`);
  }
  async login() { return (this.identity ??= await this.request('/user')).login; }
}
export function objectURL(url) {
  const match = /^https:\/\/github\.com\/([A-Za-z0-9-]+)\/([A-Za-z0-9_.-]+)\/(issues|pull)\/([1-9][0-9]*)$/.exec(url);
  if (!match) throw new Error(`Unsupported tracked GitHub URL: ${url}`);
  return { repo: `${match[1]}/${match[2]}`, kind: match[3], number: match[4] };
}
const deliveryRoot = home => join(home, 'state/github-feedback');
const sessionPath = (home, id) => join(home, 'data', taskId(id), 'github-session.json');
export async function registerOwner(home, id, ctx) {
  return withLock(home, join(deliveryRoot(home), `owner-${taskId(id)}.lock`), async () => {
    const meta = await metadata(home, id);
    if (meta.harness !== 'pi' || !meta.spawn_gen || await fs.realpath(meta.worktree) !== await fs.realpath(ctx.cwd)) {
      throw new Error('Pi worker does not match the current Firstmate task generation/worktree');
    }
    const file = ctx.sessionManager.getSessionFile();
    if (!file) throw new Error('GitHub task workers require a persisted Pi session');
    const previous = await readJSON(sessionPath(home, id), null);
    if (previous?.generation === meta.spawn_gen && previous.sessionFile !== file) {
      throw new Error(`Resume the recorded Pi session before handling feedback: ${previous.sessionFile}`);
    }
    if (previous && previous.pid !== process.pid && alive(previous.pid)) throw new Error('Another Pi process still owns this task');
    const owner = { schema: 'firstmate-github-session.v1', task: id, sessionFile: file,
      sessionId: ctx.sessionManager.getSessionId(), pid: process.pid,
      generation: meta.spawn_gen, worktree: meta.worktree, branch: meta.branch };
    await atomicJSON(sessionPath(home, id), owner);
    return owner;
  });
}
export async function currentOwner(home, id, owner) {
  const meta = await metadata(home, id);
  const saved = await readJSON(sessionPath(home, id), null);
  return meta.harness === 'pi' && meta.spawn_gen === owner.generation && meta.worktree === owner.worktree && meta.branch === owner.branch
    && saved?.pid === process.pid && saved?.sessionFile === owner.sessionFile;
}
async function snapshot(home) {
  const data = JSON.parse(await nativeCall(home, 'snapshot'));
  if (data.unreadable_records) throw new Error('Firstmate contribution ownership is unreadable');
  return data.rows;
}
async function ownReply(home, event) {
  const marker = /<!-- firstmate-feedback:([a-f0-9]{64}) -->/.exec(event.body ?? '');
  if (!marker) return false;
  const intent = await readJSON(join(deliveryRoot(home), 'replies', `${marker[1]}.json`), null);
  return intent && intent.body === event.body && intent.login === event.user?.login;
}
async function reviewThreads(client, repo, number) {
  const [owner, name] = repo.split('/');
  const threads = [];
  let cursor = null;
  for (let page = 0; page < 100; page++) {
    const result = await client.request('/graphql', { method: 'POST', body: {
      query: 'query($owner:String!,$name:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$cursor){nodes{id isResolved comments(first:1){nodes{databaseId}}}pageInfo{hasNextPage endCursor}}}}}',
      variables: { owner, name, number: Number(number), cursor },
    } });
    const batch = result.data?.repository?.pullRequest?.reviewThreads;
    if (result.errors || !batch?.nodes || !batch.pageInfo) throw new Error('GitHub review thread observation failed; cursor retained');
    threads.push(...batch.nodes.map(thread => [thread.id, thread.isResolved, thread.comments.nodes[0]?.databaseId]));
    if (!batch.pageInfo.hasNextPage) return threads.sort();
    cursor = batch.pageInfo.endCursor;
    if (!cursor) break;
  }
  throw new Error('GitHub review thread pagination bound reached; cursor retained');
}
async function observe(client, url) {
  const { repo, number, kind } = objectURL(url);
  const base = `/repos/${repo}`;
  const core = await client.request(`${base}/${kind === 'pull' ? 'pulls' : 'issues'}/${number}`);
  const comments = await client.list(`${base}/issues/${number}/comments`);
  const events = comments.map(comment => ({ ...comment, type: 'comment' }));
  let state = { state: core.state, title: core.title, body: core.body, labels: (core.labels ?? []).map(label => label.name).sort() };
  if (kind === 'pull') {
    const [reviews, inline, checks, statuses, threads] = await Promise.all([
      client.list(`${base}/pulls/${number}/reviews`), client.list(`${base}/pulls/${number}/comments`),
      client.list(`${base}/commits/${core.head.sha}/check-runs`, 'check_runs'),
      client.list(`${base}/commits/${core.head.sha}/statuses`),
      reviewThreads(client, repo, number),
    ]);
    events.push(...reviews.map(review => ({ ...review, type: 'review' })),
      ...inline.map(comment => ({ ...comment, type: 'inline' })));
    state = { ...state, head: core.head.sha, merged: core.merged, draft: core.draft, mergeable: core.mergeable, threads,
      reviews: reviews.map(review => [review.id, review.state, review.commit_id]),
      checks: checks.map(check => [check.id, check.name, check.status, check.conclusion]).sort(),
      statuses: statuses.map(status => [status.id, status.context, status.state]).sort() };
    const closing = await client.request(`${base}/pulls/${number}`);
    if (closing.head.sha !== core.head.sha) throw new Error('PR revision changed during observation; retrying next poll');
  }
  return { events, state };
}
export async function pollFeedback(home, settings, client, { signal } = {}) {
  return withLock(home, join(deliveryRoot(home), 'poll.lock'), async () => {
    const escalations = [];
    for (const row of await snapshot(home)) {
      signal?.throwIfAborted();
      try {
        objectURL(row.url);
        const path = join(deliveryRoot(home), 'objects', `${digest(row.url)}.json`);
        const saved = await readJSON(path, { seen: [], pending: [], state: null });
        const observation = await observe(client, row.url);
        const seen = new Set(saved.seen);
        for (const item of observation.events) {
          if (item.state === 'PENDING' || await ownReply(home, item)) continue;
          const event = { type: item.type, source: item.html_url, author: item.user?.login,
            authority: item.user?.login === settings.owner ? 'owner-direction' : 'review-input',
            body: item.body ?? '', revision: item.commit_id ?? observation.state.head ?? null,
            state: item.state, path: item.path, line: item.line, commentId: item.in_reply_to_id ?? item.id };
          const id = digest([row.url, item.type, item.id, item.updated_at ?? item.submitted_at, item.body, item.state]);
          if (!seen.has(id) && !saved.pending.some(pending => pending.id === id)) saved.pending.push({ id, url: row.url, ...event });
        }
        const state = digest(observation.state);
        if (state !== saved.state) {
          saved.stateVersion = (saved.stateVersion ?? 0) + 1;
          const id = digest([row.url, saved.stateVersion, state]);
          if (!seen.has(id) && !saved.pending.some(event => event.id === id)) saved.pending.push({ id, url: row.url,
            type: 'state', source: row.url, authority: 'observation', ...observation.state });
          saved.state = state;
        }
        // Queue and observation move together, before any delivery attempt.
        await atomicJSON(path, saved);
        const owners = [];
        for (const id of row.tasks ?? [row.task]) {
          try {
            const meta = await metadata(home, id);
            const session = await readJSON(sessionPath(home, id), null);
            if (meta.harness === 'pi' && session?.generation === meta.spawn_gen && meta.worktree === session.worktree) owners.push(id);
          } catch (error) { if (error.code !== 'ENOENT') throw error; }
        }
        if (owners.length !== 1) {
          if (saved.pending.length) escalations.push({ url: row.url, tasks: row.tasks, reason: 'Assign or recover one recorded Pi owner', pending: saved.pending.map(event => event.id) });
          continue;
        }
        const id = owners[0];
        const session = await readJSON(sessionPath(home, id), null);
        if (saved.pending.length && !alive(session?.pid)) escalations.push({ url: row.url, task: id,
          sessionFile: session?.sessionFile, reason: 'Resume the recorded Pi owner; feedback remains in its durable task inbox',
          pending: saved.pending.map(event => event.id) });
        for (const event of [...saved.pending]) {
          signal?.throwIfAborted();
          await nativeCall(home, 'enqueue', [id], { input: prefix + JSON.stringify(event), signal });
          saved.seen.push(event.id);
          saved.pending = saved.pending.filter(pending => pending.id !== event.id);
          await atomicJSON(path, saved);
        }
      } catch (error) {
        signal?.throwIfAborted();
        escalations.push({ url: row.url, reason: error.message });
      }
    }
    return escalations;
  });
}
export async function inboxEvents(home, id) {
  const directory = join(home, 'state', `${taskId(id)}.inbox`);
  let files;
  try { files = await fs.readdir(directory); } catch (error) { if (error.code === 'ENOENT') return []; throw error; }
  const events = [];
  for (const name of files.filter(name => /^[0-9]+\.msg$/.test(name)).sort()) {
    const path = join(directory, name);
    try {
      const body = await nativeCall(home, 'read', [path]);
      if (body.startsWith(prefix)) events.push({ path, event: JSON.parse(body.slice(prefix.length)) });
    } catch (error) { if (!await fs.stat(path).catch(() => null)) continue; throw error; }
  }
  return events;
}
export async function pendingEvent(home, id, eventId) {
  if (!/^[a-f0-9]{64}$/.test(eventId)) throw new Error('Invalid GitHub event ID');
  const entry = (await inboxEvents(home, id)).find(entry => entry.event.id === eventId);
  if (!entry) throw new Error('GitHub event is not pending in this task inbox');
  return entry;
}
export async function reply(home, id, eventId, text, client) {
  if (!text.trim() || text.length > 60000) throw new Error('Reply must contain 1..60000 characters');
  const { event } = await pendingEvent(home, id, eventId);
  const { repo, number } = objectURL(event.url);
  const body = `${text}\n\n<!-- firstmate-feedback:${eventId} -->`;
  const receiptPath = join(deliveryRoot(home), 'replies', `${eventId}.json`);
  const previous = await readJSON(receiptPath, null);
  if (previous && previous.body !== body) throw new Error('This event already has a different reply intent; inspect GitHub before changing it');
  const login = await client.login();
  await atomicJSON(receiptPath, { body, login, source: previous?.source });
  const endpoint = event.type === 'inline' ? `/repos/${repo}/pulls/${number}/comments` : `/repos/${repo}/issues/${number}/comments`;
  const found = (await client.list(endpoint)).find(comment => comment.body === body && comment.user?.login === login);
  const result = found ?? await client.request(event.type === 'inline' ? `${endpoint}/${event.commentId}/replies` : endpoint, { method: 'POST', body: { body } });
  await atomicJSON(receiptPath, { body, login, source: result.html_url });
  return result.html_url;
}
export async function finishEvent(home, id, eventId, summary, needsFirstmate) {
  if (!summary.trim() || /[\r\n]/.test(summary) || summary.length > 2000) throw new Error('Outcome must be one nonempty line (up to 2000 characters)');
  const { path } = await pendingEvent(home, id, eventId);
  const log = join(home, 'state', `${taskId(id)}.status`);
  const line = `${needsFirstmate ? `needs-decision [key=github-${eventId.slice(0, 16)}]` : 'note'}: GitHub ${eventId} ${summary}\n`;
  // Outcome precedes acknowledgment; an interrupted retry can append a harmless duplicate status line.
  await fs.appendFile(log, line, { mode: 0o600 });
  await fs.mkdir(join(dirname(path), 'handled'), { recursive: true, mode: 0o700 });
  await fs.rename(path, join(dirname(path), 'handled', path.split('/').at(-1)));
}
export async function configurePaseo(path, home) {
  const saved = await readJSON(path, {});
  saved.agents ??= {}; saved.agents.providers ??= {};
  const provider = { extends: 'pi', enabled: true, label: 'Firstmate', command: [join(root, 'bin/firstmate'), 'rpc'],
    env: { FIRSTMATE_HOME: resolve(home), FM_BACKEND: 'zellij' } };
  const previous = saved.agents.providers.firstmate;
  const legacy = { extends: 'pi', label: 'Firstmate', command: provider.command, env: { FIRSTMATE_HOME: resolve(home) } };
  if (previous && JSON.stringify(previous) !== JSON.stringify(provider) && JSON.stringify(previous) !== JSON.stringify(legacy)) throw new Error('Existing Paseo firstmate provider differs; preserve it and reconcile explicitly');
  saved.agents.providers.firstmate = provider;
  await atomicJSON(path, saved);
}
export async function configurePi(path) {
  const saved = await readJSON(path, {});
  saved.extensions ??= [];
  if (!Array.isArray(saved.extensions) || saved.extensions.some(entry => typeof entry !== 'string')) throw new Error('Preserve and reconcile the existing Pi extensions configuration');
  for (const name of ['firstmate-github.mjs', 'firstmate-peers.mjs', 'firstmate-tasks.mjs', 'firstmate-bedrock-router.mjs']) {
    const extension = join(root, 'pi/extensions', name);
    if (!saved.extensions.includes(extension)) saved.extensions.push(extension);
  }
  await atomicJSON(path, saved);
}
export async function configurePiRouter(path) {
  const saved = await readJSON(path, {});
  const template = await readJSON(join(root, 'pi/bedrock-router.models.json'));
  saved.providers ??= {};
  if (typeof saved.providers !== 'object' || Array.isArray(saved.providers)) throw new Error('Preserve and reconcile the existing Pi providers configuration');
  const expected = template.providers['bedrock-router'];
  const previous = saved.providers['bedrock-router'];
  if (previous && JSON.stringify(previous) !== JSON.stringify(expected)) throw new Error('Existing Pi bedrock-router provider differs; preserve it and reconcile explicitly');
  saved.providers['bedrock-router'] = expected;
  await atomicJSON(path, saved);
}
export async function intake(home, url, client) {
  const { repo, number, kind } = objectURL(url);
  const id = `github-${digest(url).slice(0, 16)}`;
  const input = JSON.parse(await nativeCall(home, 'snapshot-input'));
  const existing = input.backlog?.records?.find(record => record.structured && record.id === id);
  if (existing) {
    if (!(existing.links ?? []).includes(url)) throw new Error('Existing task ID has different GitHub ownership');
    return existing;
  }
  const object = await client.request(`/repos/${repo}/${kind === 'pull' ? 'pulls' : 'issues'}/${number}`);
  const added = JSON.parse(await nativeCall(home, 'task-add', [id, `${object.title} ${url}`, '--kind', 'ship', '--repo', repo.split('/')[1],
    ...(kind === 'pull' ? ['--pr', url] : []), '--body', `Work and acceptance criteria: ${url}. Firstmate owns dispatch and delivery policy.`, '--json']));
  return added.task ?? added;
}
if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  const [action, argument] = process.argv.slice(2);
  const home = resolve(process.env.FIRSTMATE_HOME || process.env.FM_HOME || join(process.env.HOME, 'src/firstmate'));
  try {
    if (action === 'configure-pi') await configurePi(argument || join(process.env.HOME, '.pi/agent/settings.json'));
    else if (action === 'configure-pi-router') await configurePiRouter(argument || join(process.env.HOME, '.pi/agent/models.json'));
    else if (action === 'configure-paseo') await configurePaseo(argument || join(process.env.PASEO_HOME || join(process.env.HOME, '.paseo'), 'config.json'), home);
    else if (action === 'intake') console.log(JSON.stringify(await intake(home, argument, new GitHub()), null, 2));
    else if (action === 'poll') {
      const settings = await config(home);
      if (!settings) throw new Error('Enable github-feedback.json in the Firstmate home first');
      console.log(JSON.stringify(await pollFeedback(home, settings, new GitHub()), null, 2));
    } else throw new Error('Usage: firstmate github intake <issue-or-PR-url> | poll | configure-paseo [config.json]');
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
