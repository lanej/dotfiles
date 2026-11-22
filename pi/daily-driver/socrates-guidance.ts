import { readFile } from "node:fs/promises";

export async function socratesGuidance(): Promise<string> {
  try {
    const skill = new URL("../../ai/skills/socrates/", import.meta.url);
    const [entrypoint, procedure] = await Promise.all([
      readFile(new URL("SKILL.md", skill), "utf8"),
      readFile(new URL("references/dialogue.txt", skill), "utf8"),
    ]);
    return [
      entrypoint,
      procedure,
      "# Pi host adapter",
      "Apply the dialogue, evidence, internal coverage properties (including Harmony and Parsimony), and readiness rules above. Revisit relevant properties after a substantive change. Surface concrete gaps, not the checklist.",
      "Use the bound Beads brief and managed attempt for session resolution. The provided draft is the scaffold and decision record. Do not create .socrates files or use another host's pointers.",
      "Investigate with read-only tools. Select the highest-impact unresolved decision, save its open decision and exact question with draft_socrates_specification, then ask it with ask_user_question. Offer choices only for meaningful alternatives. Otherwise use typed input. An interrupted or cancelled question remains open. Stop and wait for the operator to reopen it with /socrates.",
      "After a recorded answer, apply it to the decision and requirements and save the updated draft. An answer only settles what it actually addresses. If the brief already satisfies readiness, save a draft without asking a question.",
      "The operator freezes the specification with /spec-freeze. After freeze the lead drafts the task graph. /plan-approve authorizes implementation and creates Beads child tasks.",
    ].join("\n\n");
  } catch (cause) {
    throw new Error(
      "Cannot load the shared Socrates procedure from the installed dotfiles checkout",
      { cause },
    );
  }
}
