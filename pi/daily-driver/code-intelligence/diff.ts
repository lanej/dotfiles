import {
  getLanguageFromPath,
  highlightCode,
  type Theme,
} from "@earendil-works/pi-coding-agent";
import { homedir } from "node:os";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import {
  getCapabilities,
  hyperlink,
  visibleWidth,
  wrapTextWithAnsi,
} from "@earendil-works/pi-tui";

const clean = (text: string) =>
  text.replaceAll("\t", "   ").replace(/\p{Cc}/gu, " ");
type Highlighter = (text: string, language: string) => string[];
export function syntaxDiffRows(
  diff: string,
  path: string,
  theme: Theme,
  width: number,
  cwd: string,
  highlight: Highlighter = highlightCode,
): string[] {
  if (width < 3) return [];
  const lines = diff.split("\n").map((line) => {
    const match = /^([+\- ])(\s*\d+) (.*)$/u.exec(line);
    return {
      raw: line,
      prefix: match?.[1],
      number: match?.[2],
      code: clean(match?.[3] ?? ""),
    };
  });
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
  const body = lines.flatMap((line) => {
    const previous = line.prefix === "+" ? undefined : old[before++];
    const current = line.prefix === "-" ? undefined : updated[after++];
    if (line.prefix === undefined)
      return [theme.fg("toolDiffContext", clean(line.raw))];
    const tone =
      line.prefix === "+"
        ? "toolDiffAdded"
        : line.prefix === "-"
          ? "toolDiffRemoved"
          : "toolDiffContext";
    return [
      `${theme.fg(tone, `${line.prefix}${line.number ?? ""} `)}${line.prefix === "-" ? (previous ?? line.code) : (current ?? line.code)}`,
    ];
  });
  const inner = Math.max(1, width - 2);
  const rawPath = path.startsWith("~/")
    ? resolve(homedir(), path.slice(2))
    : resolve(cwd, path);
  const label = theme.fg("accent", clean(path));
  const pathLabel = getCapabilities().hyperlinks
    ? hyperlink(label, pathToFileURL(rawPath).href)
    : label;
  return [
    "",
    `${theme.fg("toolTitle", theme.bold("edit"))} ${pathLabel}`,
    "",
    ...body,
    "",
  ]
    .flatMap((line) => wrapTextWithAnsi(line, inner))
    .map((line) =>
      theme.bg(
        "toolSuccessBg",
        ` ${line}${" ".repeat(Math.max(0, width - 1 - visibleWidth(line)))}`,
      ),
    );
}
