import {
  Markdown,
  matchesKey,
  parseKey,
  truncateToWidth,
  visibleWidth,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";
import type { Component, MarkdownTheme } from "@earendil-works/pi-tui";
import { selectorLinks, selectorText } from "./text.ts";

export interface SelectorItem {
  readonly label: string;
  readonly description: string;
  readonly details?: string | undefined;
  /** Caller-rendered terminal annotations, including OSC 8 links. */
  readonly annotations?: readonly string[] | undefined;
}

export interface SelectorTheme {
  accent: (text: string) => string;
  muted: (text: string) => string;
  bold: (text: string) => string;
  selected: (text: string) => string;
  markdown: MarkdownTheme;
}

export interface SelectorOptions {
  title: string;
  context?: string | undefined;
  annotations?: readonly string[] | undefined;
  items: readonly SelectorItem[];
  theme: SelectorTheme;
  /** Available rows, read again on each render so resizing works. */
  height: () => number;
  requestRender: () => void;
  /** Undefined means cancelled; selection always requires Enter. */
  onSelect: (index: number | undefined) => void;
}

export interface SelectorComponent extends Component {
  handleInput: (input: string) => void;
}

interface SelectorContent {
  title: string;
  context?: string | undefined;
  annotations?: readonly string[] | undefined;
}

enum NavigationKey {
  Up = "up",
  Down = "down",
  Escape = "escape",
  Enter = "enter",
  Cancel = "ctrl+c",
  VimUp = "k",
  VimDown = "j",
}

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

export function selectorHints(visibleChoices: number): string[] {
  if (visibleChoices <= hintKeys.length)
    return hintKeys.slice(0, visibleChoices);
  // Reserve the last key as a prefix when the viewport needs extra hints.
  return [...hintKeys.slice(0, -1), ...hintKeys.map((key) => `l${key}`)].slice(
    0,
    visibleChoices,
  );
}

function oneLine(value: string): string {
  return selectorText(value).replace(/\s+/gu, " ");
}

function markdownRows(
  value: string | undefined,
  width: number,
  theme: SelectorTheme,
): string[] {
  return value === undefined
    ? []
    : new Markdown(selectorText(value), 0, 0, theme.markdown).render(width);
}

function joinBlocks(blocks: string[][]): string[] {
  return blocks
    .filter((block) => block.length > 0)
    .flatMap((block, index) => (index === 0 ? block : ["", ...block]));
}

function annotationBlock(items: readonly string[], width: number): string[] {
  return items.length === 0 ? [] : wrapTextWithAnsi(items.join("\n"), width);
}

function details(
  prompt: SelectorContent,
  choice: SelectorItem,
  theme: SelectorTheme,
  width: number,
): string[] {
  const heading = [
    theme.bold(selectorLinks(oneLine(choice.label))),
    selectorLinks(choice.description),
  ]
    .filter(Boolean)
    .join("\n");
  return joinBlocks([
    wrapTextWithAnsi(selectorLinks(prompt.title), width),
    markdownRows(prompt.context, width, theme),
    wrapTextWithAnsi(heading, width),
    markdownRows(choice.details, width, theme),
    annotationBlock(
      [...(prompt.annotations ?? []), ...(choice.annotations ?? [])],
      width,
    ),
  ]);
}

const columnDivider = " │ ";
const splitWidth = 50;

function preview(
  choice: SelectorItem,
  theme: SelectorTheme,
  width: number,
): string[] {
  return joinBlocks([
    choice.description === ""
      ? []
      : wrapTextWithAnsi(selectorLinks(choice.description), width),
    markdownRows(choice.details, width, theme),
    annotationBlock(choice.annotations ?? [], width),
  ]);
}

function previewColumns(
  width: number,
  choiceWidth: number,
  choices: string[],
  details: string[],
  height: number,
  theme: SelectorTheme,
): string[] {
  const detailWidth = width - choiceWidth - columnDivider.length;
  return Array.from({ length: height }, (_, index) => {
    const choice = choices[index] ?? panelRow(choiceWidth, "", theme);
    const detail = panelRow(detailWidth, details[index] ?? "", theme);
    const divider =
      details.length > 0 ? columnDivider : " ".repeat(columnDivider.length);
    return `${choice}${theme.muted(divider)}${detail}`;
  });
}

function panelRow(
  width: number,
  text: string,
  theme: SelectorTheme,
  focused = false,
): string {
  const inner = Math.max(1, width - 2);
  const clipped = truncateToWidth(text, inner);
  const padding = " ".repeat(Math.max(0, width - 1 - visibleWidth(clipped)));
  const row = ` ${clipped}${padding}`;
  return focused ? theme.selected(row) : row;
}

export function createSelector(options: SelectorOptions): SelectorComponent {
  const { theme, items: choices, requestRender, onSelect } = options;
  const prompt = options;
  if (choices.length === 0)
    throw new RangeError("A selector needs at least one item");
  let finished = false;
  const complete = (index: number | undefined) => {
    if (finished) return;
    finished = true;
    onSelect(index);
  };
  let view = View.Choices;
  let focused = 0;
  let first = 0;
  let rows = choices.slice(0, maxVisibleChoices);
  let visibleHints = selectorHints(rows.length);
  let prefix = "";
  let scroll = 0;
  let maxScroll = 0;
  const cancel = () => {
    complete(undefined);
  };
  return {
    invalidate() {},
    render(width) {
      const inner = Math.max(1, width - 2);
      const height = Math.max(3, options.height());
      const panel = (line: string) => panelRow(width, line, theme);

      if (view === View.Details) {
        const choice = choices[focused];
        const body =
          choice === undefined ? [] : details(prompt, choice, theme, inner);
        maxScroll = Math.max(0, body.length - height);
        scroll = Math.min(scroll, maxScroll);
        return body.slice(scroll, scroll + height).map(panel);
      }

      const title = wrapTextWithAnsi(
        theme.accent(selectorLinks(prompt.title)),
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
      visibleHints = selectorHints(rows.length);
      const hintWidth = visibleHints.at(-1)?.length ?? 1;

      const list = rows.map((choice, offset) => {
        const index = first + offset;
        const active = index === focused;
        const marker = active ? "→ " : "  ";
        const hint = visibleHints[offset];
        const label =
          view === View.Hints && hint !== undefined
            ? hint.startsWith(prefix)
              ? `${theme.accent(theme.bold(hint.padEnd(hintWidth)))} `
              : " ".repeat(hintWidth + 1)
            : "";
        const name = selectorLinks(oneLine(choice.label));
        const expandable =
          choice.details !== undefined || (choice.annotations?.length ?? 0) > 0;
        const text = expandable ? `${name} ${theme.accent("▸")}` : name;
        const description = selectorLinks(oneLine(choice.description));
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
          : preview(choice, theme, previewWidth).slice(0, previewHeight);
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
      return [...title.slice(0, titleHeight).map(panel), panel(""), ...body];
    },
    handleInput(input) {
      if (finished) return;
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
        if (escaped || matchesKey(input, SelectorKey.Back)) view = View.Choices;
        else if (down) scroll = Math.min(maxScroll, scroll + 1);
        else if (up) scroll = Math.max(0, scroll - 1);
      } else if (escaped) {
        cancel();
        return;
      } else if (matchesKey(input, NavigationKey.Enter)) {
        complete(focused);
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
      requestRender();
    },
  };
}
