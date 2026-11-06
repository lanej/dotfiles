import { realpath } from 'node:fs/promises';
import { nativeCall } from '../../firstmate/github-feedback.mjs';

const parameters = {
  type: 'object', additionalProperties: false, required: ['questions'],
  properties: { questions: {
    type: 'array', minItems: 1, maxItems: 4,
    items: {
      type: 'object', additionalProperties: false, required: ['question', 'header', 'options'],
      properties: {
        question: { type: 'string', minLength: 1, description: 'Complete, self-contained question' },
        header: { type: 'string', minLength: 1, maxLength: 12, description: 'Unique short label for this question' },
        options: {
          type: 'array', minItems: 2, maxItems: 4,
          items: {
            type: 'object', additionalProperties: false, required: ['label', 'description'],
            properties: {
              label: { type: 'string', minLength: 1, description: 'Unique choice label; do not add Other, Type something., or Next' },
              description: { type: 'string', description: 'What choosing this option means' },
            },
          },
        },
      },
    },
  } },
};

export function registerQuestions(pi, requireOwner, active, audience = 'user') {
  pi.registerTool({
    name: 'ask_user_question', label: 'Ask Questions',
    description: `Ask the ${audience} 1–4 questions with 2–4 choices each through native Paseo question cards. They can always type another answer. Use for needed information, preferences, or decisions. Cancellation is not an answer or approval.`,
    // WHY: Paseo's structured question adapter holds one active dialog per session.
    executionMode: 'sequential',
    parameters,
    async execute(_id, params, signal, _onUpdate, ctx) {
      if (!active() || !ctx.hasUI) throw new Error('Open this conversation in Paseo before asking native questions');
      await requireOwner(signal);
      const { questions } = params;
      const unique = values => new Set(values).size === values.length;
      if (!unique(questions.map(question => question.header)) || !unique(questions.map(question => question.question)) ||
          questions.some(question => !question.header.trim() || !question.question.trim() ||
            !unique(question.options.map(option => option.label)) ||
            question.options.some(option => !option.label.trim() || ['Other', 'Type something.', 'Next'].includes(option.label)))) {
        throw new Error('Questions need distinct nonempty headers, question text, and choice labels; typed answers are added by Paseo');
      }
      const details = { answers: [], cancelled: false };
      for (const question of questions) {
        const choices = question.options.map((option, index) => `${index + 1}. ${option.label} — ${option.description}`);
        const other = `${choices.length + 1}. Type something.`;
        const selected = signal?.aborted ? undefined : await ctx.ui.select(question.question, [...choices, other], { signal });
        if (selected === undefined || signal?.aborted) { details.cancelled = true; break; }
        const index = choices.indexOf(selected);
        if (index >= 0) {
          details.answers.push({ question: question.question, kind: 'option', answer: question.options[index].label });
        } else if (selected === other) {
          const answer = await ctx.ui.input(question.question, 'Your answer', { signal });
          if (answer === undefined || !answer.trim() || signal?.aborted) { details.cancelled = true; break; }
          details.answers.push({ question: question.question, kind: 'custom', answer });
        } else {
          throw new Error('Paseo returned an unrecognized question selection');
        }
      }
      return { content: [{ type: 'text', text: JSON.stringify(details) }], details };
    },
  });
  pi.on('before_agent_start', event => active() ? {
    systemPrompt: `${event.systemPrompt}\nYou have ask_user_question available. Use it to request needed ${audience} information, preferences, or decisions through Paseo's question cards. Offer meaningful choices; the ${audience} can also type an answer. A cancelled question provides no answer or approval. Preserve any unanswered decision and wait for ${audience} input. Task workers must record question or decision status before asking and update it after an answer.`,
  } : undefined);
}

export default function firstmateQuestions(pi) {
  const home = process.env.FM_HOME ?? process.env.FIRSTMATE_HOME;
  if (!home || process.env.FM_TASK_ID || process.env.PASEO_TASK_ROLE) return;
  let captain = false;
  registerQuestions(pi, async signal => {
    if (await nativeCall(home, 'owns-primary', [], { signal }) !== 'yes') {
      throw new Error('The current session does not own the Firstmate captain lock');
    }
  }, () => captain, 'captain');
  pi.on('session_start', async (_event, ctx) => {
    captain = ctx.mode === 'rpc' && await realpath(ctx.cwd) === await realpath(home);
  });
  pi.on('session_shutdown', () => { captain = false; });
}
