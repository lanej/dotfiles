import type {
  ExtensionAPI,
  ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { z } from "zod";
import { prUrl } from "./delivery-record.ts";
import { githubLink, renderReferences } from "./github-links.ts";
import { isEntry, PiEntryType } from "./runtime.ts";

const entryType = "pi-driver:transcript-event";
const controlFree = (value: string) => value.replace(/\p{Cc}/gu, " ").trim();

export enum VerificationOutcome {
  Passed = "passed",
  Failed = "failed",
  Review = "review",
}

export enum TranscriptEventKind {
  Verification = "verification",
  Octo = "octo",
}

const eventSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal(TranscriptEventKind.Verification),
    outcome: z.enum(VerificationOutcome),
    bead: z.string(),
    detail: z.string().max(4000),
  }),
  z.object({
    kind: z.literal(TranscriptEventKind.Octo),
    url: prUrl,
    notice: z.string().optional(),
    detail: z.string().max(4000).optional(),
  }),
]);

const verificationStyle = {
  [VerificationOutcome.Passed]: ["●", "success", "Verification passed"],
  [VerificationOutcome.Failed]: ["×", "error", "Verification failed"],
  [VerificationOutcome.Review]: ["◇", "warning", "Verification needs review"],
} as const;

export function registerTranscriptEvents(pi: ExtensionAPI): void {
  pi.registerEntryRenderer(entryType, (entry, { expanded }, theme) => {
    const parsed = eventSchema.safeParse(entry.data);
    if (!parsed.success) return undefined;
    const event = parsed.data;
    const detail = (event.detail ?? "").replace(/(?!\n)\p{Cc}/gu, " ").trim();
    const fold = detail === "" ? "" : theme.fg("dim", expanded ? "▾ " : "▸ ");
    let title: string;
    if (event.kind === TranscriptEventKind.Octo) {
      const caption = event.notice === undefined ? "Tracking" : "Octo receipt";
      title = `${theme.fg("muted", caption)} · ${theme.fg("accent", githubLink(event.url) ?? event.url)}`;
    } else {
      const [glyph, tone, caption] = verificationStyle[event.outcome];
      title = `${theme.fg(tone, `${glyph} ${caption}`)} · ${controlFree(event.bead)}`;
    }
    const refs =
      expanded && detail !== ""
        ? `\n  ${renderReferences(detail, (text) => theme.fg("accent", text)).replaceAll("\n", "\n  ")}`
        : "";
    return new Text(`${fold}${title}${refs}`, 1, 0);
  });
}

export function appendVerificationEvent(
  pi: ExtensionAPI,
  outcome: VerificationOutcome,
  bead: string,
  detail: string,
): void {
  pi.appendEntry(entryType, {
    kind: TranscriptEventKind.Verification,
    outcome,
    bead,
    detail: detail.slice(0, 4000),
  });
}

export function appendOctoEvents(
  pi: ExtensionAPI,
  ctx: ExtensionContext,
  url: string,
  receipts: { id: string; body: string }[],
): void {
  const seen = new Set(
    ctx.sessionManager.getBranch().flatMap((entry) => {
      if (!isEntry(entry, PiEntryType.Custom) || entry.customType !== entryType)
        return [];
      const parsed = eventSchema.safeParse(entry.data);
      return parsed.success &&
        parsed.data.kind === TranscriptEventKind.Octo &&
        parsed.data.url === url
        ? [parsed.data.notice]
        : [];
    }),
  );
  if (!seen.has(undefined))
    pi.appendEntry(entryType, { kind: TranscriptEventKind.Octo, url });
  for (const { id, body } of receipts) {
    if (seen.has(id)) continue;
    pi.appendEntry(entryType, {
      kind: TranscriptEventKind.Octo,
      url,
      notice: id,
      detail: body.slice(0, 4000),
    });
    seen.add(id);
  }
}
