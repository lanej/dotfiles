import { realpath } from 'node:fs/promises';
import { nativeCall } from '../../firstmate/github-feedback.mjs';
import { board, show, renderBoard, renderTask } from '../../firstmate/tasks.mjs';

const schema = properties => ({ type: 'object', properties, additionalProperties: false });
const result = (text, details) => ({ content: [{ type: 'text', text }], details });

export default function firstmateTasks(pi) {
  const home = process.env.FM_HOME ?? process.env.FIRSTMATE_HOME;
  if (!home || process.env.FM_TASK_ID) return;
  let captain = false;
  async function requireCaptain() {
    if (!captain || await nativeCall(home, 'owns-primary') !== 'yes') throw new Error('Resume the existing Firstmate captain before inspecting its tasks');
  }
  pi.registerTool({
    name: 'firstmate_task_board', label: 'Firstmate task board',
    description: 'Read authoritative task status, open captain decisions, queued/deferred work, recent completed outcomes, and observation limits. all reveals more retained rows; never infer completion from a PR or historical event.',
    parameters: schema({ all: { type: 'boolean', description: 'Reveal all rows available in the native snapshot instead of the compact view' } }),
    async execute(_id, params, signal) {
      await requireCaptain();
      const snapshot = await board(home, { all: params.all, signal });
      return result(renderBoard(snapshot), snapshot);
    },
  });
  pi.registerTool({
    name: 'firstmate_task_show', label: 'Firstmate task detail',
    description: 'Read one exact local task ID, its full canonical backlog record and current snapshot observations. Qualified secondmate IDs belong to their own home.',
    parameters: { ...schema({ taskId: { type: 'string', description: 'Exact local task ID from the task board' } }), required: ['taskId'] },
    async execute(_id, params, signal) {
      await requireCaptain();
      const task = await show(home, params.taskId, { signal });
      return result(renderTask(task), task);
    },
  });
  pi.registerCommand('tasks', {
    description: 'Show the Firstmate task board; /tasks all expands it and /tasks <id> shows local task detail',
    async handler(args) {
      await requireCaptain();
      const input = args.trim();
      const details = !input || input === 'all' ? await board(home, { all: input === 'all' }) : await show(home, input);
      pi.sendMessage({ customType: 'firstmate-task-board', display: true, details,
        content: !input || input === 'all' ? renderBoard(details) : renderTask(details) });
    },
  });
  pi.on('session_start', async (_event, ctx) => { captain = await realpath(ctx.cwd) === await realpath(home); });
  pi.on('session_shutdown', () => { captain = false; });
  pi.on('before_agent_start', event => captain ? {
    systemPrompt: `${event.systemPrompt}\nFor task tracking, use firstmate_task_board and firstmate_task_show. Give every accepted assignment a durable ID through the existing native task intake before dispatch and include that ID in updates, blockers, and completion replies. Acknowledge queued work with its ID. When asked for tasks or status, show a compact board in this conversation with current states, what is waiting on the captain, and recent outcomes; disclose unknown or omitted observations. Keep canonical task ownership and lifecycle unchanged. Peer message requests remain separate from managed tasks.`,
  } : undefined);
}
