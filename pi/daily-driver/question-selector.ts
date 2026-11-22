import type { ExtensionContext, Theme } from "@earendil-works/pi-coding-agent";
import {
  matchesKey,
  parseKey,
  truncateToWidth,
  visibleWidth,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";
import type { QuestionEvidence } from "./question-evidence.ts";
import {
  questionLinks,
  questionText,
  renderQuestionEvidence,
} from "./question-links.ts";
import { NavigationKey } from "./runtime.ts";

export interface QuestionChoice {
  label: string;
  description: string;
  details?: string | undefined;
  evidence?: QuestionEvidence[] | undefined;
}

interface Question {
  question: string;
  context?: string | undefined;
  evidence?: QuestionEvidence[] | undefined;
  options: QuestionChoice[];
}

export enum QuestionSelectionKind {
  Choice = "choice",
  Text = "text",
}

type QuestionSelection =
  | { kind: QuestionSelectionKind.Choice; index: number }
  | { kind: QuestionSelectionKind.Text };

enum View {
  Choices,
  Hints,
  Details,
}

enum SelectorKey {
  Hints = ";",
  Details = "l",
  Back = "h",
  Backspace = "backspace",
}

const hintKeys = Array.from("asdfghjkl");
const maxVisibleChoices = 12;

export function questionHints(visibleChoices: number): string[] {
  if (visibleChoices <= hintKeys.length)
    return hintKeys.slice(0, visibleChoices);
  // Reserve the last key as a prefix when the viewport needs extra hints.
  return [...hintKeys.slice(0, -1), ...hintKeys.map((key) => `l${key}`)].slice(
    0,
    visibleChoices,
  );
}

function oneLine(value: string): string {
  return questionText(value).replace(/\s+/gu, " ");
}

function evidenceRows(
  items: QuestionEvidence[],
  worktree: string,
  theme: Theme,
): string[] {
  return items.map((item) => {
    const content = renderQuestionEvidence(item, worktree);
    return "observation" in item ? content : theme.fg("accent", content);
  });
}

function details(
  prompt: Question,
  choice: QuestionChoice,
  worktree: string,
  theme: Theme,
): string {
  const paragraphs = [
    questionLinks(prompt.question),
    ...(prompt.context === undefined ? [] : [questionLinks(prompt.context)]),
    [
      theme.bold(questionLinks(oneLine(choice.label))),
      questionLinks(choice.description),
    ]
      .filter(Boolean)
      .join("\n"),
    ...(choice.details === undefined ? [] : [questionLinks(choice.details)]),
  ];
  const links = evidenceRows(
    [...(prompt.evidence ?? []), ...(choice.evidence ?? [])],
    worktree,
    theme,
  );
  if (links.length > 0) paragraphs.push(links.join("\n"));
  return paragraphs.join("\n\n");
}

const columnDivider = " │ ";
const splitWidth = 50;

function preview(
  choice: QuestionChoice,
  worktree: string,
  theme: Theme,
  width: number,
): string[] {
  const content = [
    questionLinks(choice.description),
    questionLinks(choice.details ?? ""),
    ...evidenceRows(choice.evidence ?? [], worktree, theme),
  ].filter((section) => section.length > 0);
  return wrapTextWithAnsi(content.join("\n\n"), width);
}

function previewColumns(
  width: number,
  choiceWidth: number,
  choices: string[],
  details: string[],
  height: number,
  theme: Theme,
): string[] {
  const detailWidth = width - choiceWidth - columnDivider.length;
  return Array.from({ length: height }, (_, index) => {
    const choice = choices[index] ?? panelRow(choiceWidth, "", theme);
    const detail = panelRow(detailWidth, details[index] ?? "", theme);
    const divider =
      details.length > 0 ? columnDivider : " ".repeat(columnDivider.length);
    return `${choice}${theme.fg("muted", divider)}${detail}`;
  });
}

function panelRow(
  width: number,
  text: string,
  theme: Theme,
  focused = false,
): string {
  const inner = Math.max(1, width - 2);
  const clipped = truncateToWidth(text, inner);
  const padding = " ".repeat(Math.max(0, width - 1 - visibleWidth(clipped)));
  return theme.bg(
    focused ? "selectedBg" : "userMessageBg",
    ` ${clipped}${padding}`,
  );
}

export async function chooseQuestion(
  ctx: ExtensionContext,
  prompt: Question,
  signal?: AbortSignal,
): Promise<QuestionSelection | undefined> {
  if (signal?.aborted === true) return undefined;
  const choices = [
    ...prompt.options,
    { label: "Type an answer", description: "" },
  ];
  return ctx.ui.custom<QuestionSelection | undefined>(
    (tui, theme, _keys, done) => {
      let view = View.Choices;
      let focused = 0;
      let first = 0;
      let rows = choices.slice(0, maxVisibleChoices);
      let visibleHints = questionHints(rows.length);
      let prefix = "";
      let scroll = 0;
      let maxScroll = 0;
      const cancel = () => {
        done(undefined);
      };
      signal?.addEventListener("abort", cancel, { once: true });
      if (signal?.aborted === true) queueMicrotask(cancel);

      return {
        dispose() {
          signal?.removeEventListener("abort", cancel);
        },
        invalidate() {},
        render(width) {
          const inner = Math.max(1, width - 2);
          const height = Math.max(3, tui.terminal.rows - 2);
          const panel = (line: string) => panelRow(width, line, theme);

          if (view === View.Details) {
            const choice = choices[focused];
            const body =
              choice === undefined
                ? []
                : wrapTextWithAnsi(
                    details(prompt, choice, ctx.cwd, theme),
                    inner,
                  );
            maxScroll = Math.max(0, body.length - height);
            scroll = Math.min(scroll, maxScroll);
            return body.slice(scroll, scroll + height).map(panel);
          }

          const title = wrapTextWithAnsi(
            theme.fg("accent", questionLinks(prompt.question)),
            inner,
          );
          const titleHeight = Math.min(
            title.length,
            Math.max(1, height - choices.length - 1),
          );
          const room = Math.max(1, height - titleHeight - 1);
          const split = width >= splitWidth;
          const previewHeight = split
            ? Math.min(6, room)
            : Math.min(4, Math.max(0, room - choices.length));
          const choiceWidth = split
            ? Math.min(32, Math.floor(width * 0.46))
            : width;
          const capacity = Math.min(
            maxVisibleChoices,
            room - (split ? 0 : previewHeight),
          );
          const start = Math.min(
            Math.max(first, focused - capacity + 1),
            focused,
            Math.max(0, choices.length - capacity),
          );
          if (
            start !== first ||
            rows.length !== Math.min(capacity, choices.length - start)
          )
            prefix = "";
          first = start;
          rows = choices.slice(first, first + capacity);
          visibleHints = questionHints(rows.length);
          const hintWidth = visibleHints.at(-1)?.length ?? 1;

          const list = rows.map((choice, offset) => {
            const index = first + offset;
            const active = index === focused;
            const marker = active ? "→ " : "  ";
            const hint = visibleHints[offset];
            const label =
              view === View.Hints && hint !== undefined
                ? hint.startsWith(prefix)
                  ? `${theme.fg("accent", theme.bold(hint.padEnd(hintWidth)))} `
                  : " ".repeat(hintWidth + 1)
                : "";
            const name = questionLinks(oneLine(choice.label));
            const expandable =
              choice.details !== undefined ||
              (choice.evidence?.length ?? 0) > 0;
            const text = expandable
              ? `${name} ${theme.fg("accent", "▸")}`
              : name;
            const description = questionLinks(oneLine(choice.description));
            const row =
              marker +
              label +
              (split || description === "" ? text : `${text} · ${description}`);
            return panelRow(choiceWidth, row, theme, active);
          });
          const choice = choices[focused];
          const previewWidth = split
            ? width - choiceWidth - columnDivider.length - 2
            : inner;
          const lines =
            choice === undefined
              ? []
              : preview(choice, ctx.cwd, theme, previewWidth).slice(
                  0,
                  previewHeight,
                );
          const body = split
            ? previewColumns(
                width,
                choiceWidth,
                list,
                lines,
                Math.max(list.length, previewHeight),
                theme,
              )
            : [
                ...list,
                ...Array.from({ length: previewHeight }, (_, index) =>
                  panel(lines[index] ?? ""),
                ),
              ];
          return [
            ...title.slice(0, titleHeight).map(panel),
            panel(""),
            ...body,
          ];
        },
        handleInput(input) {
          const escaped = matchesKey(input, NavigationKey.Escape);
          if (matchesKey(input, NavigationKey.Cancel)) {
            cancel();
            return;
          }

          const down =
            matchesKey(input, NavigationKey.VimDown) ||
            matchesKey(input, NavigationKey.Down);
          const up =
            matchesKey(input, NavigationKey.VimUp) ||
            matchesKey(input, NavigationKey.Up);
          if (view === View.Hints) {
            if (escaped) {
              view = View.Choices;
              prefix = "";
            } else if (matchesKey(input, SelectorKey.Backspace)) {
              prefix = prefix.slice(0, -1);
            } else {
              const key = parseKey(input);
              if (key !== undefined && /^[a-z]$/u.test(key)) {
                const candidate = prefix + key;
                const match = visibleHints.indexOf(candidate);
                if (match >= 0) {
                  focused = first + match;
                  prefix = "";
                  view = View.Choices;
                } else if (
                  visibleHints.some((hint) => hint.startsWith(candidate))
                ) {
                  prefix = candidate;
                }
              }
            }
          } else if (view === View.Details) {
            if (escaped || matchesKey(input, SelectorKey.Back))
              view = View.Choices;
            else if (down) scroll = Math.min(maxScroll, scroll + 1);
            else if (up) scroll = Math.max(0, scroll - 1);
          } else if (escaped) {
            cancel();
            return;
          } else if (matchesKey(input, NavigationKey.Enter)) {
            done(
              focused < prompt.options.length
                ? { kind: QuestionSelectionKind.Choice, index: focused }
                : { kind: QuestionSelectionKind.Text },
            );
            return;
          } else if (matchesKey(input, SelectorKey.Hints)) {
            view = View.Hints;
          } else if (matchesKey(input, SelectorKey.Details)) {
            scroll = 0;
            view = View.Details;
          } else if (down) {
            focused = Math.min(choices.length - 1, focused + 1);
          } else if (up) {
            focused = Math.max(0, focused - 1);
          }
          tui.requestRender();
        },
      };
    },
    {
      overlay: true,
      overlayOptions: { anchor: "center", width: "100%", margin: 1 },
    },
  );
}
