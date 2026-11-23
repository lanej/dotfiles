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
const clean = (text: string) => text.replace(/\p{Cc}/gu, " ");
export function diagnosticRows(
  value: DiagnosticSnapshot,
  theme: Pick<Theme, "fg" | "bold">,
  width: number,
  expanded: boolean,
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
  const items = [...value.diagnostics].sort(
    (a, b) =>
      Number(a.severity === "warning") - Number(b.severity === "warning"),
  );
  const visible = expanded ? items : items.slice(0, 2);
  return [
    ...wrap(theme.fg("muted", theme.bold(heading))),
    ...visible.flatMap((item) => {
      const code =
        item.code === undefined
          ? ""
          : `  ${item.source === "typescript" || item.source === "ts" ? "TS" : ""}${String(item.code)}`;
      const location = theme.fg(
        item.severity,
        theme.bold(
          `${item.severity === "error" ? "E" : "W"} ${String(item.line)}:${String(item.column)}`,
        ),
      );
      const metadata = location + theme.fg("muted", clean(code));
      const text = clean(item.message);
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
        (row, index) =>
          (index === 0 ? `${metadata}  ` : " ".repeat(gutter)) + row,
      );
    }),
    ...(items.length > visible.length
      ? wrap(
          theme.fg(
            "muted",
            `… ${String(items.length - visible.length)} more diagnostics`,
          ),
        )
      : []),
    ...(value.freshness === "unversioned"
      ? wrap(theme.fg("muted", "Server did not report a document version"))
      : []),
  ];
}
