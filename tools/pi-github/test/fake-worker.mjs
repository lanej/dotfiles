import { randomUUID } from 'node:crypto';
let attempt;
let started = false;
const pending = new Map();
function send(data) { if (process.connected) process.send({ ...data, attempt }); }
function tool(name, args = {}) {
  const id = randomUUID();
  return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); send({ type: 'tool', id, name, args }); });
}
function finish(data) { send(data); if (process.connected) process.disconnect(); }
process.on('disconnect', () => process.exit(0));
process.on('message', async message => {
  if (message.type === 'tool_result') {
    const request = pending.get(message.id); pending.delete(message.id);
    if (message.error) request?.reject(new Error(message.error)); else request?.resolve(message.result);
  }
  if (message.type === 'abort') {
    send({ type: 'done', text: 'Late success must not win cancellation' });
    setTimeout(() => { if (process.connected) process.disconnect(); }, 100);
  }
  if (message.type !== 'start' || started) return;
  started = true; attempt = message.attempt;
  send({ type: 'progress', text: 'Controlled worker started' });
  const mode = process.env.PG_TEST_MODE;
  if (mode === 'hang') return;
  if (mode === 'transient' && attempt === 1) { finish({ type: 'failure', error: 'Provider rate limit (429)' }); return; }
  if (mode === 'auth') { finish({ type: 'failure', error: 'Authentication required' }); return; }
  try {
    if (message.task.kind === 'resolve_conflict') {
      await tool('read_conflict');
      await tool('write_resolution', { policy: { maxAttempts: mode === 'wrong-side' ? 5 : 3, timeoutSeconds: 60, retryDelaySeconds: 1 } });
      await tool('validate_resolution');
    } else if (mode === 'missing-read') { /* Controlled contract violation. */ }
    else await tool('read_pull_request');
    finish({ type: 'done', text: 'Controlled test result' });
  } catch (error) { finish({ type: 'failure', error: error.message }); }
});
