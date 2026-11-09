import { ProcessTerminal, TuiAltScreen, matchesKey, Key, truncateToWidth, visibleWidth, wrapTextWithAnsi, type Component, type Terminal } from "@earendil-works/pi-tui";
import { cleanText, type Snapshot } from "./domain.js";
import { Coordinator } from "./coordinator.js";

const cyan = (s: string) => `\x1b[36m${s}\x1b[0m`;
const dim = (s: string) => `\x1b[2m${s}\x1b[0m`;
function state(s: string): string { const c = s === "failed" ? 31 : s === "succeeded" ? 32 : s === "conflicted" ? 33 : 36; return `\x1b[${c}m${s}\x1b[0m`; }
export interface ViewState { selected: number; expanded: boolean; scroll: number; message: string }
export function renderDashboard(snapshot: Snapshot, view: ViewState, width: number, height: number): string[] {
  width = Math.max(1, width); height = Math.max(1, height);
  const fit = (s: string, size = width) => truncateToWidth(s, Math.max(1, size), "");
  const job = snapshot.jobs[view.selected];
  const rows = [fit(cyan(" PI / GITHUB ") + ` ${snapshot.scheduler}  ·  worker ${snapshot.worker}  ·  ${snapshot.jobs.length} jobs`), ...wrapTextWithAnsi(dim(" j/k select · enter details · p pause · c cancel · r retry · [/] scroll · q quit"), width)];
  if (snapshot.recoveryPid) rows.push(fit(state("Recovering") + ` — waiting for previous worker PID ${snapshot.recoveryPid} to exit`));
  if (view.message) rows.push(fit(view.message));
  const bodyHeight = Math.max(2, Math.floor((height - rows.length - 3) * 0.6));
  const offset = Math.max(0, view.selected - bodyHeight + 1);
  const queue = [cyan(" QUEUE"), ...snapshot.jobs.slice(offset, offset + bodyHeight - 1).map((j, index) => `${offset + index === view.selected ? "›" : " "} ${j.id.slice(0, 8)} ${state(j.status)} ${j.task.kind === "resolve_conflict" ? "merge conflict" : "PR summary"}`)];
  if (!snapshot.jobs.length) queue.push(dim(" No jobs yet. Run pi-github demo."));
  const details = job ? [cyan(` ${job.task.kind} / attempt ${job.attempts.length}`), ` ${job.id}`, ` ${state(job.status)}`, ...(job.error ? wrapTextWithAnsi(cleanText(job.error), Math.max(1, width - 40)) : []), ...wrapTextWithAnsi(cleanText(job.result ?? (snapshot.events.filter(e => e.jobId === job.id && (e.kind === "conflicted" || e.kind === "progress")).at(-1)?.detail ?? "Waiting for worker output…")), Math.max(1, width >= 90 ? width - 40 : width)).slice(view.scroll)] : [dim(" Select a job to inspect its state.")];
  if (width >= 90 && !view.expanded) {
    const leftWidth = 36;
    for (let i = 0; i < bodyHeight; i++) { const left = fit(queue[i] ?? "", leftWidth); rows.push(left + " ".repeat(Math.max(0, leftWidth - visibleWidth(left))) + dim(" │ ") + fit(details[i] ?? "", width - leftWidth - 3)); }
  } else {
    rows.push(...queue.slice(0, view.expanded ? 1 : Math.min(4, bodyHeight)), ...details.slice(0, Math.max(1, bodyHeight - (view.expanded ? 1 : 4))));
  }
  rows.push(fit(dim("─".repeat(width))), fit(cyan(" TRANSITIONS / PROGRESS")));
  const relevant = snapshot.events.filter(e => !job || e.jobId === job.id);
  const events = relevant.flatMap(e => wrapTextWithAnsi(`${new Date(e.at).toISOString().slice(11, 19)} ${e.kind}  ${cleanText(e.detail, 2000)}`, width));
  const remaining = Math.max(0, height - rows.length - 1);
  const end = Math.max(0, events.length - view.scroll);
  rows.push(...events.slice(Math.max(0, end - remaining), end));
  while (rows.length < height - 1) rows.push("");
  rows.push(fit(dim(job ? ` ${job.id.slice(0, 8)} · ${job.status} · ${job.attempts.length} attempts` : " Ready for submitted work")));
  return rows.slice(0, height).map(line => fit(line));
}
export class Dashboard implements Component {
  view: ViewState = { selected: 0, expanded: false, scroll: 0, message: "" };
  constructor(private coordinator: Coordinator, private height: () => number, private refresh: () => void, private quit: () => void) {}
  invalidate(): void {}
  render(width: number): string[] { return renderDashboard(this.coordinator.snapshot(), this.view, width, this.height()); }
  handleInput(input: string): void {
    const snapshot = this.coordinator.snapshot();
    const job = snapshot.jobs[this.view.selected];
    try {
      if (input === "q" || matchesKey(input, Key.ctrl("c"))) { this.quit(); return; }
      if (input === "j" || matchesKey(input, Key.down)) { this.view.selected = Math.min(snapshot.jobs.length - 1, this.view.selected + 1); this.view.scroll = 0; }
      else if (input === "k" || matchesKey(input, Key.up)) { this.view.selected = Math.max(0, this.view.selected - 1); this.view.scroll = 0; }
      else if (matchesKey(input, Key.enter)) this.view.expanded = !this.view.expanded;
      else if (input === "p") this.coordinator.command({ op: snapshot.scheduler === "paused" ? "resume" : "pause" });
      else if (input === "c" && job) this.coordinator.command({ op: "cancel", id: job.id });
      else if (input === "r" && job) this.coordinator.command({ op: "retry", id: job.id });
      else if (input === "[") this.view.scroll += 3;
      else if (input === "]") this.view.scroll = Math.max(0, this.view.scroll - 3);
      this.view.selected = Math.max(0, this.view.selected); this.view.message = "";
    } catch (error) { this.view.message = cleanText((error as Error).message); }
    this.refresh();
  }
}
export async function dashboard(coordinator: Coordinator, terminal: Terminal = new ProcessTerminal()): Promise<void> {
  const tui = new TuiAltScreen(terminal, false, undefined, { mouse: false, copyOnSelect: false });
  let quitting = false;
  let end!: () => void;
  const finished = new Promise<void>(resolve => { end = resolve; });
  const quit = () => { if (!quitting) { quitting = true; void coordinator.close().finally(end); } };
  const component = new Dashboard(coordinator, () => terminal.rows, () => tui.requestRender(), quit);
  const changed = () => tui.requestRender();
  coordinator.on("change", changed);
  process.on("SIGINT", quit); process.on("SIGTERM", quit);
  try { tui.addChild(component); tui.setFocus(component); tui.start(); await finished; }
  finally { coordinator.off("change", changed); process.off("SIGINT", quit); process.off("SIGTERM", quit); tui.stop(); await coordinator.close(); }
}
