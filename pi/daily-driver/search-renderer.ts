import {
  type ExtensionAPI,
  type Theme,
  getLanguageFromPath,
  highlightCode,
} from "@earendil-works/pi-coding-agent";
import { type Component, Text, wrapTextWithAnsi } from "@earendil-works/pi-tui";
import { z } from "zod";

const MAX_HIGHLIGHT_BYTES = 50_000;
const commandArgs = z.object({ command: z.string() });
const shellCallArgs = commandArgs.extend({ timeout: z.number().optional() });

type ShellWord = { raw: string; start: number };

function simpleCommand(input: string): ShellWord[] {
  const command = input.trim();
  const leading = input.length - input.trimStart().length;
  const words: ShellWord[] = [];
  let end = 0;
  for (const token of command.matchAll(
    /'[^'\r\n]*'|"[^"\r\n]*"|[^\s'"|&;<>`$\\()]+/gu,
  )) {
    const gap = command.slice(end, token.index);
    if (words.length > 0 && !/^[ \t]+$/u.test(gap)) return [];
    if (words.length === 0 && token.index !== 0) return [];
    const raw = token[0];
    words.push({ raw, start: leading + token.index });
    end = token.index + raw.length;
  }
  return end === command.length ? words : [];
}

function highlightShellCommand(command: string, theme: Theme): string {
  const bash = (text: string) => highlightCode(text, "bash").join("\n");
  const [executable, ...args] = simpleCommand(command);
  if (executable === undefined || !/^[\w./-]+$/u.test(executable.raw))
    return bash(command);

  let rendered =
    command.slice(0, executable.start) +
    theme.fg("syntaxFunction", theme.bold(executable.raw));
  let end = executable.start + executable.raw.length;
  for (const { raw, start } of args) {
    if (raw === "--") break;
    const flag = /^--?[A-Za-z][\w-]*(?==|$)/u.exec(raw)?.[0];
    if (flag === undefined) continue;
    rendered +=
      bash(command.slice(end, start)) + theme.fg("syntaxKeyword", flag);
    end = start + flag.length;
  }
  return rendered + bash(command.slice(end));
}

type Highlighter = (text: string, language: string) => string[];

export function highlightSearchOutput(
  tool: string,
  args: unknown,
  output: string,
  highlight: Highlighter = highlightCode,
): string {
  if (
    Buffer.byteLength(output) > MAX_HIGHLIGHT_BYTES ||
    output.includes("\x1b")
  )
    return output;
  const parsed = commandArgs.safeParse(args);
  const words =
    tool === "bash" && parsed.success
      ? simpleCommand(parsed.data.command).map(({ raw }) =>
          raw.startsWith("'") || raw.startsWith('"') ? raw.slice(1, -1) : raw,
        )
      : [];
  const [command, option, script, file] = words;

  // The native shell renderer owns the truncation footer and exit-status text.
  const footer =
    /\n\n\[(?:Showing[^\n]*Full output:|Command exited with code)[\s\S]*$/u.exec(
      output,
    );
  const text = footer === null ? output : output.slice(0, footer.index);

  if (
    command === "sed" &&
    option === "-n" &&
    words.length === 4 &&
    script !== undefined &&
    /^\d+(?:,(?:\d+|\$))?p$/u.test(script) &&
    file !== undefined
  ) {
    const language = getLanguageFromPath(file);
    if (language !== undefined)
      return highlight(text, language).join("\n") + (footer?.[0] ?? "");
  }

  if (tool !== "grep" && command !== "rg") return output;
  if (
    command === "rg" &&
    words.some((arg) =>
      /^--(?:json|count(?:-matches)?|files(?:-with(?:out)?-matches)?|replace)(?:=|$)/u.test(
        arg,
      ),
    )
  )
    return output;
  const last = words.at(-1);
  const singleFile =
    command === "rg" &&
    ((words.length === 3 && option?.startsWith("-") === false) ||
      (words.length === 4 &&
        (option === "-n" || option === "--line-number"))) &&
    last !== undefined &&
    !/^[~-]|[*?]/u.test(last)
      ? getLanguageFromPath(last)
      : undefined;
  return (
    text
      .split("\n")
      .map((line) => {
        const match = /^(.+?)([:-])(\d+)\2(.*)$/u.exec(line);
        const filePath = match?.[1];
        const code = match?.[4];
        const language =
          filePath === undefined ? undefined : getLanguageFromPath(filePath);
        if (language !== undefined && code !== undefined) {
          const prefix = line.slice(0, line.length - code.length);
          return prefix + highlight(code, language).join("\n");
        }
        if (singleFile !== undefined) {
          const numbered = /^(\d+[:-])(.*)$/u.exec(line);
          const source = numbered?.[2];
          if (source !== undefined)
            return (
              (numbered?.[1] ?? "") + highlight(source, singleFile).join("\n")
            );
          if (words.length === 3 && line !== "" && !line.startsWith("rg:"))
            return highlight(line, singleFile).join("\n");
        }
        return line;
      })
      .join("\n") + (footer?.[0] ?? "")
  );
}

const outputDetails = z
  .object({
    truncation: z.object({ truncated: z.boolean().optional() }).optional(),
    fullOutputPath: z.string().optional(),
    matchLimitReached: z.number().optional(),
    linesTruncated: z.boolean().optional(),
  })
  .loose();

export function registerSearchRendering(pi: ExtensionAPI): void {
  const painted = new WeakSet<Component>();
  pi.registerToolRenderer((name, next) => {
    const base = next();
    if (name !== "bash" && name !== "grep") return base;
    const render = base?.renderResult;
    if (render === undefined) return base;
    const renderCall = base?.renderCall;
    return {
      ...base,
      ...(name === "bash" && renderCall !== undefined
        ? {
            renderCall(args, theme, context) {
              // Let Pi start its tool timer and reuse its width-aware text component.
              const component = renderCall(args, theme, context);
              const parsed = shellCallArgs.safeParse(args);
              if (!parsed.success || !(component instanceof Text))
                return component;
              const { command, timeout } = parsed.data;
              if (
                command.trim() === "" ||
                command.includes("\x1b") ||
                Buffer.byteLength(command) > MAX_HIGHLIGHT_BYTES
              )
                return component;
              const prompt = theme.fg("toolTitle", theme.bold("$"));
              const syntax = highlightShellCommand(command, theme);
              const suffix =
                timeout !== undefined && timeout !== 0
                  ? theme.fg("muted", ` (timeout ${timeout.toString()}s)`)
                  : "";
              component.setText(`${prompt} ${syntax}${suffix}`);
              return component;
            },
          }
        : {}),
      renderResult(result, options, theme, context) {
        const fallback = () =>
          render(
            result,
            options,
            theme,
            context.lastComponent !== undefined &&
              painted.has(context.lastComponent)
              ? { ...context, lastComponent: undefined }
              : context,
          );
        const block = result.content[0];
        if (
          options.isPartial ||
          result.isError === true ||
          result.content.length !== 1 ||
          block?.type !== "text"
        )
          return fallback();
        const details = outputDetails.safeParse(result.details);
        if (
          details.success &&
          (details.data.truncation?.truncated === true ||
            details.data.fullOutputPath !== undefined ||
            details.data.matchLimitReached !== undefined ||
            details.data.linesTruncated === true)
        )
          return fallback();
        const args: unknown = context.args;
        const highlighted = highlightSearchOutput(name, args, block.text);
        if (highlighted === block.text) return fallback();

        const component: Component = {
          invalidate() {},
          render(width) {
            const rows = wrapTextWithAnsi(
              highlighted.trimEnd(),
              Math.max(1, width),
            );
            const limit = name === "bash" ? 5 : 15;
            if (options.expanded || rows.length <= limit) return ["", ...rows];
            const hidden = rows.length - limit;
            const hint = theme.fg("muted", `… ${hidden.toString()} more lines`);
            return name === "bash"
              ? ["", hint, ...rows.slice(-limit)]
              : ["", ...rows.slice(0, limit), hint];
          },
        };
        painted.add(component);
        return component;
      },
    };
  });
}
