import {
  selectorLink as questionLink,
  selectorLinks as questionLinks,
  selectorText as questionText,
} from "@lanej/pi-components";
import { hyperlink } from "@earendil-works/pi-tui";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import type { QuestionEvidence } from "./evidence.ts";

export { questionLink, questionLinks, questionText };

export function renderQuestionEvidence(
  evidence: QuestionEvidence,
  worktree: string,
): string {
  if ("url" in evidence) return questionLink(evidence.label, evidence.url);
  if ("observation" in evidence)
    return [
      questionText(evidence.label),
      questionLinks(evidence.observation),
    ].join("\n");

  const target = pathToFileURL(resolve(worktree, evidence.path));
  const location =
    evidence.line === undefined
      ? evidence.path
      : `${evidence.path}:${String(evidence.line)}`;
  if (evidence.line !== undefined) target.hash = `L${String(evidence.line)}`;
  const label = questionText(evidence.label).replace(/\s+/gu, " ");
  return hyperlink(`${label} · ${location}`, target.href);
}
