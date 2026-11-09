import { ProcessTerminal, TuiAltScreen, matchesKey, Key, type Component, type Terminal } from "@earendil-works/pi-tui";
import { cleanText } from "./domain.js";
import { Coordinator } from "./coordinator.js";
import { layoutDashboard, type ViewState } from "./dashboard-render.js";
export { renderDashboard, type ViewState } from "./dashboard-render.js";

export class Dashboard implements Component {
  view: ViewState = { selected: 0, expanded: false, scroll: 0, message: "" };
  constructor(private coordinator: Coordinator, private height: () => number, private refresh: () => void, private quit: () => void) {}
  private limits = { resultLimit: 0, activityLimit: 0 };
  private width = 0;
  invalidate(): void {}
  render(width: number): string[] {
    this.width = width;
    if (this.height() < 18 || width < 32) this.view.focus = "result";
    const layout = layoutDashboard(this.coordinator.snapshot(), this.view, width, this.height());
    this.limits = layout;
    this.view.scroll = Math.min(this.view.scroll, layout.resultLimit);
    this.view.activityScroll = Math.min(this.view.activityScroll ?? 0, layout.activityLimit);
    return layout.lines;
  }
  handleInput(input: string): void {
    if (this.height() < 18 || this.width < 32) this.view.focus = "result";
    const snapshot = this.coordinator.snapshot();
    const job = snapshot.jobs[this.view.selected];
    try {
      if (input === "q" || matchesKey(input, Key.ctrl("c"))) { this.quit(); return; }
      if (input === "j" || matchesKey(input, Key.down)) { this.view.selected = Math.min(snapshot.jobs.length - 1, this.view.selected + 1); this.view.scroll = 0; this.view.activityScroll = 0; }
      else if (input === "k" || matchesKey(input, Key.up)) { this.view.selected = Math.max(0, this.view.selected - 1); this.view.scroll = 0; this.view.activityScroll = 0; }
      else if (matchesKey(input, Key.enter)) this.view.expanded = !this.view.expanded;
      else if (input === "p") this.coordinator.command({ op: snapshot.scheduler === "paused" ? "resume" : "pause" });
      else if (input === "c" && job) this.coordinator.command({ op: "cancel", id: job.id });
      else if (input === "r" && job) this.coordinator.command({ op: "retry", id: job.id });
      else if (matchesKey(input, Key.tab) && this.height() >= 18 && this.width >= 32) this.view.focus = this.view.focus === "activity" ? "result" : "activity";
      else if (input === "[" || input === "]") {
        const field = this.view.focus === "activity" ? "activityScroll" : "scroll";
        const limit = field === "scroll" ? this.limits.resultLimit : this.limits.activityLimit;
        const direction = (input === "[" ? -3 : 3) * (field === "activityScroll" ? -1 : 1);
        this.view[field] = Math.min(limit, Math.max(0, (this.view[field] ?? 0) + direction));
      }
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
