import {
  getMarkdownTheme,
  type ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { createSelector } from "@lanej/pi-components";
import type { QuestionEvidence } from "./evidence.ts";
import { renderQuestionEvidence } from "./links.ts";
import type { SpecQuestion } from "./spec.ts";

export enum QuestionSelectionKind {
  Choice = "choice",
  Text = "text",
}

type QuestionSelection =
  | { kind: QuestionSelectionKind.Choice; index: number }
  | { kind: QuestionSelectionKind.Text };

export async function chooseQuestion(
  ctx: ExtensionContext,
  prompt: SpecQuestion,
  signal?: AbortSignal,
): Promise<QuestionSelection | undefined> {
  if (signal?.aborted === true) return undefined;
  return ctx.ui.custom<QuestionSelection | undefined>(
    (tui, theme, _keys, done) => {
      const annotations = (items: QuestionEvidence[] | undefined) =>
        (items ?? []).map((item) => {
          const content = renderQuestionEvidence(item, ctx.cwd);
          return "observation" in item ? content : theme.fg("accent", content);
        });
      const cancel = () => {
        done(undefined);
      };
      const selector = createSelector({
        title: prompt.question,
        context: prompt.context,
        annotations: annotations(prompt.evidence),
        items: [
          ...prompt.options.map((item) => ({
            ...item,
            annotations: annotations(item.evidence),
          })),
          { label: "Type an answer", description: "" },
        ],
        theme: {
          accent: (text) => theme.fg("accent", text),
          muted: (text) => theme.fg("muted", text),
          bold: (text) => theme.bold(text),
          selected: (text) => theme.style(text, { bg: "selectedBg" }),
          markdown: getMarkdownTheme(),
        },
        height: () => tui.terminal.rows - 2,
        requestRender: () => {
          tui.requestRender();
        },
        onSelect(index) {
          done(
            index === undefined
              ? undefined
              : index < prompt.options.length
                ? { kind: QuestionSelectionKind.Choice, index }
                : { kind: QuestionSelectionKind.Text },
          );
        },
      });
      signal?.addEventListener("abort", cancel, { once: true });
      if (signal?.aborted === true) queueMicrotask(cancel);
      return {
        ...selector,
        dispose() {
          signal?.removeEventListener("abort", cancel);
        },
      };
    },
    {
      overlay: true,
      overlayOptions: {
        anchor: "center",
        width: "100%",
        margin: { top: 1, bottom: 1 },
      },
    },
  );
}
