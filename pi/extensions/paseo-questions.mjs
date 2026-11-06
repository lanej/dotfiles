import { registerQuestions } from './firstmate-questions.mjs';

export default function paseoQuestions(pi) {
  if (!['manager', 'worker'].includes(process.env.PASEO_TASK_ROLE)) return;
  let active = false;
  registerQuestions(pi, async () => {}, () => active);
  pi.on('session_start', (_event, ctx) => { active = ctx.mode === 'rpc'; });
  pi.on('session_shutdown', () => { active = false; });
}
