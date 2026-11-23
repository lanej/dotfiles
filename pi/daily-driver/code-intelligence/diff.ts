import {
  getLanguageFromPath,
  highlightCode,
  type Theme,
} from "@earendil-works/pi-coding-agent";
import { defaultMinSplitColumns, type DriverConfig } from "../config.ts";
import { diagnosticGlyph, type DiagnosticSnapshot } from "./diagnostics.ts";
import { homedir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import {
  getCapabilities,
  hyperlink,
  sliceByColumn,
  stripTerminalSequences,
  visibleWidth,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";

const clean = (text: string) =>
  text.replaceAll("\t", "   ").replace(/\p{Cc}/gu, " ");
type Highlighter = (text: string, language: string) => string[];
type DiffTheme = Pick<Theme, "fg" | "bg" | "bold">;
interface DiffLine {
  raw: string;
  prefix: string | undefined;
  number: string;
  beforeNumber: string;
  afterNumber: string;
  code: string;
  rawCode: string;
  before: string | undefined;
  after: string | undefined;
}

function parseDiffLines(diff: string): DiffLine[] {
  const lines: DiffLine[] = diff.split("\n").map((line) => {
    const match = /^([+\- ])(\s*\d+) (.*)$/u.exec(line);
    return {
      raw: line,
      prefix: match?.[1],
      number: match?.[2]?.trim() ?? "",
      beforeNumber: "",
      afterNumber: "",
      code: clean(match?.[3] ?? ""),
      rawCode: match?.[3] ?? "",
      before: undefined,
      after: undefined,
    };
  });
  let delta = 0;
  for (const line of lines) {
    line.beforeNumber = line.prefix === "+" ? "" : line.number;
    line.afterNumber =
      line.prefix === " "
        ? String(Number(line.number) + delta)
        : line.prefix === "+"
          ? line.number
          : "";
    if (line.prefix === "+") delta++;
    else if (line.prefix === "-") delta--;
  }
  return lines;
}

export function inlineDiagnosticLines(diff: string): ReadonlySet<number> {
  return new Set(
    parseDiffLines(diff).flatMap(({ afterNumber }) =>
      afterNumber === "" ? [] : [Number(afterNumber)],
    ),
  );
}

type Issue = DiagnosticSnapshot["diagnostics"][number];

function undercurl(
  row: string,
  line: DiffLine,
  issues: Issue[],
  offset: number,
): string {
  const edges = new Map<number, number>();
  const rowWidth = visibleWidth(row);
  const lineNumber = Number(line.afterNumber);
  for (const issue of issues) {
    if (issue.endColumn === undefined || issue.endLine === undefined) continue;
    const start =
      issue.line === lineNumber
        ? visibleWidth(clean(line.rawCode.slice(0, issue.column - 1)))
        : 0;
    const end =
      issue.endLine === lineNumber
        ? visibleWidth(clean(line.rawCode.slice(0, issue.endColumn - 1)))
        : visibleWidth(line.code);
    const from = Math.max(0, start - offset);
    const to = Math.min(rowWidth, end - offset);
    if (from >= to) continue;
    edges.set(from, (edges.get(from) ?? 0) + 1);
    edges.set(to, (edges.get(to) ?? 0) - 1);
  }
  if (edges.size === 0) return row;
  let position = 0;
  let depth = 0;
  let result = "";
  for (const [edge, change] of [...edges].sort(([a], [b]) => a - b)) {
    const span = sliceByColumn(row, position, edge - position);
    result +=
      depth > 0
        ? `\x1b[4:3m${span.replaceAll("\x1b[0m", "\x1b[0m\x1b[4:3m")}\x1b[24m`
        : span;
    depth += change;
    position = edge;
  }
  return `${result}${sliceByColumn(row, position, rowWidth - position)}\x1b[39m`;
}

export function syntaxDiffRows(
  diff: string,
  path: string,
  theme: DiffTheme,
  width: number,
  cwd: string,
  highlight: Highlighter = highlightCode,
  display: DriverConfig["display"] = {
    min_split_columns: defaultMinSplitColumns,
    inline_diagnostics: true,
  },
  diagnostics: DiagnosticSnapshot["diagnostics"] = [],
): string[] {
  if (width < 3) return [];
  const lines = parseDiffLines(diff);
  const language = getLanguageFromPath(path);
  const paint = (added: boolean) => {
    const source = lines
      .filter((line) => line.prefix !== (added ? "-" : "+"))
      .map((line) => line.code);
    return language === undefined || Buffer.byteLength(diff) > 64 * 1024
      ? source
      : highlight(source.join("\n"), language);
  };
  const old = paint(false),
    updated = paint(true);
  let before = 0,
    after = 0;
  for (const line of lines) {
    line.before = line.prefix === "+" ? undefined : old[before++];
    line.after = line.prefix === "-" ? undefined : updated[after++];
  }
  const issuesByLine = new Map<string, Issue[]>();
  const activeIssues = display.inline_diagnostics ? diagnostics : [];
  for (const issue of activeIssues) {
    const number = String(issue.line);
    const issues = issuesByLine.get(number);
    if (issues === undefined) issuesByLine.set(number, [issue]);
    else issues.push(issue);
  }
  const inner = Math.max(1, width - 2);
  const digits = lines.reduce(
    (digits, line) =>
      Math.max(digits, line.beforeNumber.length, line.afterNumber.length),
    1,
  );
  const leftWidth = Math.floor((inner - 3) / 2);
  const rightWidth = inner - 3 - leftWidth;
  const gutter = digits + 2;
  const split = leftWidth - gutter >= display.min_split_columns;
  const pad = (text: string, columns: number) =>
    text + " ".repeat(Math.max(0, columns - visibleWidth(text)));
  const toolBackground = theme.bg("toolSuccessBg", "").replace("\x1b[49m", "");
  const background = (line: DiffLine, row: string): string => {
    const color =
      line.prefix === "+"
        ? display.added_background
        : line.prefix === "-"
          ? display.removed_background
          : undefined;
    if (color === undefined) return row;
    const rgb = [1, 3, 5].map((offset) =>
      Number.parseInt(color.slice(offset, offset + 2), 16),
    );
    const start = `\x1b[48;2;${rgb.join(";")}m`;
    return (
      start +
      row.replaceAll("\x1b[0m", `\x1b[0m${start}`) +
      (toolBackground === "" ? "\x1b[49m" : toolBackground)
    );
  };
  const tone = (line: DiffLine) =>
    line.prefix === "+"
      ? "toolDiffAdded"
      : line.prefix === "-"
        ? "toolDiffRemoved"
        : "toolDiffContext";
  const cell = (
    line: DiffLine | undefined,
    side: "before" | "after",
    columns: number,
  ): string[] => {
    if (line === undefined) return [" ".repeat(columns)];
    if (line.prefix === undefined)
      return wrapTextWithAnsi(
        theme.fg("toolDiffContext", clean(line.raw)),
        columns,
      ).map((row) => pad(row, columns));
    const code = (side === "before" ? line.before : line.after) ?? line.code;
    const number = side === "before" ? line.beforeNumber : line.afterNumber;
    const issues = side === "after" ? (issuesByLine.get(number) ?? []) : [];
    const ranges =
      side === "after"
        ? activeIssues.filter(
            (issue) =>
              issue.line <= Number(number) &&
              (issue.endLine ?? issue.line) >= Number(number),
          )
        : [];
    const label = theme.fg(
      tone(line),
      `${line.prefix}${number.padStart(digits)} `,
    );
    const indent = columns > gutter ? " ".repeat(gutter) : "";
    let cursor = 0;
    const sourceRows =
      columns <= gutter
        ? wrapTextWithAnsi(label + code, columns)
        : wrapTextWithAnsi(code, columns - gutter).map((row, index) => {
            const plain = stripTerminalSequences(row);
            const start = line.code.indexOf(plain, cursor);
            if (start >= 0) cursor = start + plain.length;
            const marked =
              start < 0
                ? row
                : undercurl(
                    row,
                    line,
                    ranges,
                    visibleWidth(line.code.slice(0, start)),
                  );
            return (index === 0 ? label : indent) + marked;
          });
    const inlayRows: string[] = [];
    for (const issue of issues) {
      const inlay = `${theme.fg(issue.severity, diagnosticGlyph(issue.severity))} ${theme.fg("muted", clean(issue.message))}`;
      const last = sourceRows.at(-1);
      if (
        last !== undefined &&
        inlayRows.length === 0 &&
        visibleWidth(last) + 2 + visibleWidth(inlay) <= columns
      )
        sourceRows[sourceRows.length - 1] = `${last}  ${inlay}`;
      else
        inlayRows.push(
          ...wrapTextWithAnsi(inlay, columns - indent.length).map(
            (row) => indent + row,
          ),
        );
    }
    return [
      ...sourceRows.map((row) => background(line, pad(row, columns))),
      ...inlayRows.map((row) => pad(row, columns)),
    ];
  };
  const paired = (
    left: DiffLine | undefined,
    right: DiffLine | undefined,
  ): string[] => {
    const oldRows = cell(left, "before", leftWidth),
      newRows = cell(right, "after", rightWidth);
    return Array.from(
      { length: Math.max(oldRows.length, newRows.length) },
      (_unused, row) =>
        (oldRows[row] ?? " ".repeat(leftWidth)) +
        theme.fg("dim", " │ ") +
        (newRows[row] ?? " ".repeat(rightWidth)),
    );
  };
  const body: string[] = [];
  if (split) {
    body.push(
      pad(theme.fg("muted", "Before"), leftWidth) +
        theme.fg("dim", " │ ") +
        theme.fg("muted", "After"),
    );
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (line?.prefix === "-" || line?.prefix === "+") {
        const removed: DiffLine[] = [],
          added: DiffLine[] = [];
        while (lines[index]?.prefix === "-") {
          const value = lines[index++];
          if (value !== undefined) removed.push(value);
        }
        while (lines[index]?.prefix === "+") {
          const value = lines[index++];
          if (value !== undefined) added.push(value);
        }
        for (let row = 0; row < Math.max(removed.length, added.length); row++)
          body.push(...paired(removed[row], added[row]));
      } else {
        body.push(...paired(line, line));
        index++;
      }
    }
  } else {
    for (const line of lines)
      body.push(...cell(line, line.prefix === "-" ? "before" : "after", inner));
  }
  const rawPath = path.startsWith("~/")
    ? resolve(homedir(), path.slice(2))
    : resolve(cwd, path);
  const label = theme.fg("accent", clean(path));
  const pathLabel = getCapabilities().hyperlinks
    ? hyperlink(label, pathToFileURL(rawPath).href)
    : label;
  return [
    "",
    ...wrapTextWithAnsi(
      `${theme.fg("toolTitle", theme.bold("edit"))} ${pathLabel}`,
      inner,
    ),
    "",
    ...body,
    "",
  ].map((line) =>
    theme.bg(
      "toolSuccessBg",
      ` ${line}${" ".repeat(Math.max(0, width - 1 - visibleWidth(line)))}`,
    ),
  );
}
