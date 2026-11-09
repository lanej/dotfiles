import { Markdown, truncateToWidth, visibleWidth, wrapTextWithAnsi, type MarkdownTheme } from "@earendil-works/pi-tui";
import { activeStates, cleanText, type Job, type JobEvent, type Snapshot } from "./domain.js";

const paint = (code: number, text: string) => `\x1b[${code}m${text}\x1b[0m`;
const accent = (text: string) => paint(36, text);
const muted = (text: string) => paint(90, text);
const bold = (text: string) => paint(1, text);
const fit = (text: string, width: number) => truncateToWidth(text, Math.max(1, width), "");
const pad = (text: string, width: number) => fit(text, width) + " ".repeat(Math.max(0, width - visibleWidth(fit(text, width))));
const statusLabel = (value: string) => value.replaceAll("_", " ");
function state(value: string): string {
  const code = value === "failed" ? 31 : value === "succeeded" ? 32 : value === "conflicted" || value === "paused" || value === "retry_wait" ? 33 : 36;
  const icon = value === "succeeded" ? "✓" : value === "failed" ? "×" : value === "queued" ? "◇" : "●";
  return paint(code, `${icon} ${statusLabel(value)}`);
}
const title = (job: Job) => job.task.kind === "resolve_conflict" ? "Conflict resolution" : "Pull request summary";
const markdownTheme: MarkdownTheme = {
  heading: text => accent(bold(text)), link: accent, linkUrl: muted, code: accent,
  codeBlock: text => paint(37, text), codeBlockBorder: text => muted(text.length > 3 ? `╭─ ${text.slice(3)} ` : "╰────"),
  highlightCode: (code, language) => {
    if (language?.toLowerCase() === "json") {
      try { code = JSON.stringify(JSON.parse(code), null, 2); } catch { /* NOTE: Incomplete streamed JSON stays visible without reformatting. */ }
    }
    return code.split("\n").map(line => paint(37, line));
  },
  quote: muted, quoteBorder: accent, hr: muted, listBullet: accent, bold,
  italic: text => paint(3, text), strikethrough: text => paint(9, text), underline: text => paint(4, text),
};
export interface ViewState {
  selected: number; expanded: boolean; scroll: number; message: string;
  focus?: "result" | "activity"; activityScroll?: number;
}

function resultMarkdown(job: Job, events: JobEvent[]): string {
  if (job.result) {
    const text = cleanText(job.result, 24000);
    const boundary = text.lastIndexOf("\n\n");
    if (job.task.kind === "resolve_conflict" && job.status === "succeeded" && boundary >= 0) {
      try {
        const verified = JSON.parse(text.slice(boundary + 2)) as { clean?: unknown; mergeCommit?: unknown; policy?: Record<string, unknown> };
        if (verified.clean === true && typeof verified.mergeCommit === "string" && /^[a-f0-9]{40}$/.test(verified.mergeCommit) && verified.policy && ["maxAttempts", "timeoutSeconds", "retryDelaySeconds"].every(key => typeof verified.policy![key] === "number")) {
          return `${text.slice(0, boundary)}\n\n---\n\n**Independently verified** · clean two-parent merge\n\n\`\`\`json\n${JSON.stringify(verified.policy)}\n\`\`\`\n\nCommit \`${verified.mergeCommit}\``;
        }
      } catch { /* NOTE: Older or unfamiliar results remain visible as received. */ }
    }
    return text;
  }
  if (job.error) return `**${statusLabel(job.status)}**\n\n${cleanText(job.error)}`;
  const attemptStart = job.attempts.at(-1)?.startedAt ?? 0;
  const progress = events.filter(e => e.at >= attemptStart && e.kind === "progress" && !e.detail.startsWith("Using existing ")).map(e => e.detail).join("");
  if (progress) return progress;
  const conflict = events.findLast(e => e.kind === "conflicted");
  if (conflict) return `**Reconciling the two branches**\n\nPi is reading the conflict and validating a combined policy.\n\n\`\`\`diff\n${conflict.detail}\n\`\`\``;
  return job.status === "queued" ? "Waiting for the scheduler to dispatch this job." : "Waiting for worker output…";
}

function panel(label: string, contents: string[], width: number, height: number, focused = false, hint = ""): string[] {
  const border = focused ? accent : muted;
  const inside = Math.max(1, width - 4);
  const heading = ` ${label} `;
  const top = border("╭─") + (focused ? bold(heading) : heading) + border("─".repeat(Math.max(0, width - visibleWidth(heading) - 3)) + "╮");
  const rows = [top];
  for (let i = 0; i < height - 2; i++) rows.push(border("│") + " " + pad(contents[i] ?? "", inside) + " " + border("│"));
  const bottom = hint ? ` ${hint} ` : "";
  rows.push(border("╰" + "─".repeat(Math.max(0, width - visibleWidth(bottom) - 2)) + bottom + "╯"));
  return rows.slice(0, height).map(line => fit(line, width));
}

function queue(snapshot: Snapshot, selected: number, width: number, height: number): string[] {
  const capacity = Math.max(1, Math.floor((height - 2) / 4));
  const start = Math.max(0, selected - capacity + 1);
  const rows: string[] = [];
  for (const [i, job] of snapshot.jobs.slice(start, start + capacity).entries()) {
    const chosen = start + i === selected;
    rows.push((chosen ? accent("▸ ") + bold(title(job)) : "  " + title(job)), "  " + state(job.status), muted(`  ${job.id.slice(0, 8)} · attempt ${job.attempts.length}`), "");
  }
  if (!snapshot.jobs.length) rows.push("No jobs yet.", "", ...wrapTextWithAnsi(muted("Run bin/pi-github demo from another terminal."), Math.max(1, width - 4)));
  return panel(`QUEUE · ${snapshot.jobs.length}`, rows, width, height, false, snapshot.jobs.length > capacity ? `${start + 1}–${Math.min(start + capacity, snapshot.jobs.length)} of ${snapshot.jobs.length}` : "");
}

function result(job: Job | undefined, events: JobEvent[], view: ViewState, width: number, height: number): { lines: string[]; maxScroll: number } {
  if (!job) return { maxScroll: 0, lines: panel("RESULT", ["Submit a job to get started.", "", ...wrapTextWithAnsi(muted("The selected result will appear here, with the worker's Markdown formatted for the terminal."), Math.max(1, width - 4))], width, height, true) };
  const attempt = job.attempts.at(-1);
  const duration = attempt?.endedAt ? ` · ${((attempt.endedAt - attempt.startedAt) / 1000).toFixed(1)}s` : "";
  const calls = events.filter(e => e.kind === "tool" && e.at >= (attempt?.startedAt ?? 0)).length;
  const metadata = height < 10 ? [state(job.status)] : [bold(title(job)), `${state(job.status)}  ${muted(`Attempt ${job.attempts.length}${duration} · ${calls} tool${calls === 1 ? "" : "s"}`)}`, muted(job.id), ""];
  const lines = new Markdown(resultMarkdown(job, events), 0, 0, markdownTheme).render(Math.max(1, width - 4));
  const available = Math.max(1, height - 2 - metadata.length);
  const offset = Math.min(view.scroll, Math.max(0, lines.length - available));
  return { maxScroll: Math.max(0, lines.length - available), lines: panel("RESULT", [...metadata, ...lines.slice(offset, offset + available)], width, height, view.focus !== "activity", lines.length > available ? `${offset + 1}–${Math.min(offset + available, lines.length)} / ${lines.length}` : "") };
}

function activity(events: JobEvent[], view: ViewState, width: number, height: number): { lines: string[]; maxScroll: number } {
  const meaningful = events.filter(e => e.kind !== "worker_started" && (e.kind !== "progress" || e.detail.startsWith("Using existing ")));
  const capacity = Math.max(1, height - 2);
  const offset = Math.min(view.activityScroll ?? 0, Math.max(0, meaningful.length - capacity));
  const end = meaningful.length - offset;
  const rows = meaningful.slice(Math.max(0, end - capacity), end).map(e => {
    const label = e.kind === "tool" ? accent(e.detail.replaceAll("_", " ")) : e.kind === "progress" ? muted(e.detail) : e.kind === "conflicted" ? paint(33, "Merge conflict detected") : state(e.kind);
    return muted(new Date(e.at).toISOString().slice(11, 19)) + "  " + label;
  });
  return { maxScroll: Math.max(0, meaningful.length - capacity), lines: panel("ACTIVITY · UTC", rows.length ? rows : [muted("Waiting for events…")], width, height, view.focus === "activity", offset ? `${offset} earlier` : "latest") };
}

export function layoutDashboard(snapshot: Snapshot, view: ViewState, width: number, height: number): { lines: string[]; resultLimit: number; activityLimit: number } {
  let resultLimit = 0; let activityLimit = 0;
  width = Math.max(1, width); height = Math.max(1, height);
  const job = snapshot.jobs[view.selected];
  const events = snapshot.events.filter(e => !job || e.jobId === job.id);
  const completed = snapshot.jobs.filter(j => j.status === "succeeded").length;
  const waiting = snapshot.jobs.filter(j => j.status === "queued" || j.status === "retry_wait").length;
  const active = snapshot.jobs.filter(j => activeStates.includes(j.status)).length;
  const rows = [accent(bold(" π  GITHUB WORKER")) + "  " + state(snapshot.scheduler) + muted(` · worker ${snapshot.worker}`), muted(` ${snapshot.jobs.length} jobs   ${waiting} waiting   ${active} active   ${completed} succeeded`)];
  if (width < 32 || height < 12) {
    rows.push(job ? `${title(job)} · ${state(job.status)}` : "No jobs yet.", ...(job ? wrapTextWithAnsi(cleanText(job.error ?? job.result ?? "Waiting for worker output…"), width) : []));
    rows.length = Math.min(rows.length, height - 1);
    while (rows.length < height - 1) rows.push("");
    rows.push(muted("q quit · j/k jobs"));
  } else {
    if (snapshot.recoveryPid) rows[1] = paint(33, ` Waiting for previous worker PID ${snapshot.recoveryPid} to exit`);
    if (view.message) rows[1] = paint(31, " " + view.message);
    rows.push("");
    const bodyHeight = Math.max(4, height - 5);
    const sideBySide = width >= 96 && height >= 18 && !view.expanded;
    const leftWidth = sideBySide ? 30 : 0;
    const rightWidth = width - (sideBySide ? leftWidth + 2 : 0);
    const compactQueue = !sideBySide && !view.expanded ? [muted(` QUEUE · ${snapshot.jobs.length}  `) + (job ? `${title(job)}  ${state(job.status)}` : "No jobs yet."), ""] : [];
    const activityHeight = height >= 18 ? Math.min(8, Math.max(5, Math.floor(bodyHeight * 0.27))) : 0;
    const resultHeight = bodyHeight - compactQueue.length - (activityHeight ? activityHeight + 1 : 0);
    const paneView = activityHeight ? view : { ...view, focus: "result" as const };
    const output = result(job, events, paneView, rightWidth, resultHeight);
    const timeline = activityHeight ? activity(events, view, rightWidth, activityHeight) : { lines: [], maxScroll: 0 };
    resultLimit = output.maxScroll; activityLimit = timeline.maxScroll;
    const right = [...compactQueue, ...output.lines, ...(activityHeight ? ["", ...timeline.lines] : [])];
    if (sideBySide) {
      const left = queue(snapshot, view.selected, leftWidth, bodyHeight);
      for (let i = 0; i < bodyHeight; i++) rows.push(pad(left[i] ?? "", leftWidth) + "  " + (right[i] ?? ""));
    } else rows.push(...right);
    const controls = width >= 110 ? " j/k jobs · enter expand · tab result/activity · [/] scroll · p pause · c cancel · r retry · q quit" : width >= 72 ? " j/k jobs · enter expand · tab pane · [/] scroll · q quit" : " q quit · j/k jobs · [/] scroll";
    rows.push(muted(controls), muted(job ? ` ${job.id.slice(0, 8)} · ${title(job)}${view.expanded ? " · expanded" : ""}` : " Submit work with bin/pi-github demo"));
  }
  while (rows.length < height) rows.push("");
  return { lines: rows.slice(0, height).map(line => fit(line, width)), resultLimit, activityLimit };
}

export function renderDashboard(snapshot: Snapshot, view: ViewState, width: number, height: number): string[] {
  return layoutDashboard(snapshot, view, width, height).lines;
}
