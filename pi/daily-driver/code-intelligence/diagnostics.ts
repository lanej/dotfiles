import type { Theme } from "@earendil-works/pi-coding-agent";
import { visibleWidth, wrapTextWithAnsi } from "@earendil-works/pi-tui";
import { z } from "zod";
import type { Diagnostics } from "./client.ts";

export const diagnosticSnapshot = z.object({
  path: z.string(),
  state: z.enum(["received", "pending", "unavailable"]),
  version: z.number().optional(),
  freshness: z.enum(["versioned", "unversioned"]).optional(),
  message: z.string().optional(),
  total: z.number().optional(),
  truncated: z.boolean().optional(),
  diagnostics: z
    .array(
      z.object({
        line: z.number(),
        column: z.number(),
        endLine: z.number().optional(),
        endColumn: z.number().optional(),
        severity: z.enum(["error", "warning"]),
        message: z.string(),
        source: z.string().optional(),
        code: z.union([z.string(), z.number()]).optional(),
      }),
    )
    .default([]),
});
export type DiagnosticSnapshot = z.infer<typeof diagnosticSnapshot>;
export function snapshot(
  path: string,
  result: Diagnostics | undefined,
): DiagnosticSnapshot {
  if (result === undefined) return { path, state: "pending", diagnostics: [] };
  const issues = result.items.filter(
    (item) => item.severity === undefined || item.severity <= 2,
  );
  return {
    path,
    state: "received",
    version: result.version,
    freshness: result.freshness,
    total: issues.length,
    truncated: issues.length > 30,
    diagnostics: issues.slice(0, 30).map((item) => ({
      line: item.range.start.line + 1,
      column: item.range.start.character + 1,
      endLine: item.range.end.line + 1,
      endColumn: item.range.end.character + 1,
      severity: item.severity === 2 ? "warning" : "error",
      message: (typeof item.message === "string"
        ? item.message
        : item.message.value
      ).slice(0, 2000),
      ...(item.source === undefined ? {} : { source: item.source }),
      ...(item.code === undefined ? {} : { code: item.code }),
    })),
  };
}
export function diagnosticGlyph(severity: "error" | "warning") {
  return severity === "error" ? "×" : "⚠";
}
const clean = (text: string) => text.replace(/\p{Cc}/gu, " ");
function diagnosticKey(item: DiagnosticSnapshot["diagnostics"][number]) {
  return JSON.stringify([item.severity, item.message]);
}

export function groupDiagnostics(
  diagnostics: DiagnosticSnapshot["diagnostics"],
) {
  const groups = new Map<
    string,
    {
      severity: "error" | "warning";
      text: string;
      locations: Set<string>;
    }
  >();
  for (const item of diagnostics) {
    const key = diagnosticKey(item);
    const position = `${String(item.line)}:${String(item.column)}`;
    const group = groups.get(key);
    if (group === undefined) {
      groups.set(key, {
        severity: item.severity,
        text: clean(item.message),
        locations: new Set([position]),
      });
    } else {
      group.locations.add(position);
    }
  }
  return [...groups.values()].sort(
    (a, b) =>
      Number(a.severity === "warning") - Number(b.severity === "warning"),
  );
}

export function diagnosticMessageRows(
  group: ReturnType<typeof groupDiagnostics>[number],
  theme: Pick<Theme, "fg" | "bold">,
  width: number,
  expanded: boolean,
): string[] {
  const wrap = (text: string) => wrapTextWithAnsi(text, Math.max(1, width));
  const { severity, text, locations } = group;
  const positions = [...locations];
  const shown = expanded ? positions : positions.slice(0, 3);
  const remaining = positions.length - shown.length;
  const glyph = theme.fg(severity, theme.bold(diagnosticGlyph(severity)));
  const metadata = `${glyph} ${theme.fg("muted", shown.join(", ") + (remaining > 0 ? ` +${String(remaining)}` : ""))}`;
  const gutter = visibleWidth(metadata) + 2;
  // Keep enough room for the message before placing it beside its metadata.
  if (width - gutter < 40) {
    const indent = width > 2 ? "  " : "";
    return [
      ...wrap(metadata),
      ...wrapTextWithAnsi(text, Math.max(1, width - indent.length)).map(
        (row) => indent + row,
      ),
    ];
  }
  return wrapTextWithAnsi(text, width - gutter).map(
    (row, index) => (index === 0 ? `${metadata}  ` : " ".repeat(gutter)) + row,
  );
}

export function diagnosticRows(
  value: DiagnosticSnapshot,
  theme: Pick<Theme, "fg" | "bold">,
  width: number,
  expanded: boolean,
  inlineLines?: ReadonlySet<number>,
): string[] {
  const wrap = (text: string) => wrapTextWithAnsi(text, Math.max(1, width));
  if (value.state !== "received")
    return wrap(
      theme.fg(
        "muted",
        `Diagnostics · ${value.state === "pending" ? "checking…" : clean(value.message ?? "unavailable")}`,
      ),
    );
  const errors = value.diagnostics.filter(
    (item) => item.severity === "error",
  ).length;
  const warnings = value.diagnostics.filter(
    (item) => item.severity === "warning",
  ).length;
  const count = (number: number, singular: string) =>
    `${String(number)} ${singular}${number === 1 ? "" : "s"}`;
  const heading =
    value.total === 0
      ? "Diagnostics · no errors or warnings reported"
      : `Diagnostics · ${count(errors, "error")} · ${count(warnings, "warning")}${value.truncated === true ? " shown" : ""}`;
  const remaining = value.diagnostics.filter(
    (item) => inlineLines?.has(item.line) !== true,
  );
  const items = groupDiagnostics(remaining);
  const visible = expanded ? items : items.slice(0, 2);
  return [
    ...(items.length > 0 ||
    remaining.length === value.diagnostics.length ||
    value.truncated === true
      ? wrap(theme.fg("muted", theme.bold(heading)))
      : []),
    ...visible.flatMap((group) =>
      diagnosticMessageRows(group, theme, width, expanded),
    ),
    ...(items.length > visible.length
      ? wrap(
          theme.fg(
            "muted",
            `… ${count(items.length - visible.length, "more message")}`,
          ),
        )
      : []),
    ...(value.freshness === "unversioned"
      ? wrap(theme.fg("muted", "Server did not report a document version"))
      : []),
  ];
}
