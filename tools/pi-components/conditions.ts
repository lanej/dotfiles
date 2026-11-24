import {
  matchesKey,
  truncateToWidth,
  visibleWidth,
  wrapTextWithAnsi,
  type Component,
} from "@earendil-works/pi-tui";
import { selectorText } from "./text.ts";
import {
  ActivityState,
  ConditionState,
  activityIndicator,
  conditionStatus,
  conditionSummary,
  statusText,
  type Activity,
  type Condition,
  type StatusPresentation,
  type StatusTheme,
} from "./status.ts";

export interface ConditionsPanelOptions {
  title: string;
  conditions: readonly Condition[];
  activity?: Activity | undefined;
  theme: StatusTheme;
  height: () => number;
  requestRender: () => void;
  onClose?: (() => void) | undefined;
  presentation?: StatusPresentation | undefined;
}

export interface ConditionsPanel extends Component {
  handleInput: (input: string) => void;
  setConditions: (conditions: readonly Condition[]) => void;
  setActivity: (activity: Activity | undefined) => void;
  setFrame: (frame: number) => void;
  selectedId: () => string | undefined;
}

enum NavigationKey {
  Down = "down",
  Up = "up",
  Right = "right",
  Left = "left",
  Enter = "enter",
  Escape = "escape",
  Cancel = "ctrl+c",
  PageDown = "pageDown",
  PageUp = "pageUp",
  Home = "home",
  End = "end",
  VimDown = "j",
  VimUp = "k",
  Inspect = "l",
  Back = "h",
}

function snapshot(conditions: readonly Condition[]): Condition[] {
  const ids = new Set<string>();
  for (const condition of conditions) {
    if (
      condition.id.trim().length === 0 ||
      condition.label.trim().length === 0 ||
      ids.has(condition.id) ||
      !Object.values(ConditionState).includes(condition.state)
    )
      throw new RangeError(
        "Conditions need distinct nonempty IDs, labels and known states",
      );
    ids.add(condition.id);
  }
  return conditions.map((condition) => ({ ...condition }));
}

function allocation(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;
}

function fit(value: string, width: number): string {
  if (width <= 0) return "";
  const clipped = truncateToWidth(value, width);
  return clipped + " ".repeat(Math.max(0, width - visibleWidth(clipped)));
}

function conditionDetails(
  condition: Condition,
  theme: StatusTheme,
  width: number,
  presentation: StatusPresentation,
): string[] {
  const heading = [
    theme.bold(statusText(condition.label)),
    conditionStatus(condition, theme, presentation),
    ...(condition.stale === true
      ? [
          theme.muted(
            `Previous assessment: ${conditionStatus({ ...condition, stale: false }, theme, presentation)}`,
          ),
        ]
      : []),
  ].join("\n");
  const blocks = [
    heading,
    condition.summary === undefined ? "" : selectorText(condition.summary),
    condition.details === undefined ? "" : selectorText(condition.details),
  ].filter((part) => part.length > 0);
  return wrapTextWithAnsi(blocks.join("\n\n"), width);
}

export function createConditionsPanel(
  options: ConditionsPanelOptions,
): ConditionsPanel {
  const { theme, requestRender } = options;
  let conditions = snapshot(options.conditions);
  let activity =
    options.activity === undefined ? undefined : { ...options.activity };
  let frame = options.presentation?.frame;
  let selected = 0;
  let first = 0;
  let inspecting = false;
  let offset = 0;
  let maximumOffset = 0;
  let page = 1;
  let closed = false;
  const selection = () => conditions[selected];
  const close = () => {
    if (closed || options.onClose === undefined) return;
    closed = true;
    options.onClose();
  };
  const move = (delta: number) => {
    selected = Math.max(0, Math.min(conditions.length - 1, selected + delta));
    offset = 0;
  };

  return {
    invalidate() {},
    selectedId: () => selection()?.id,
    setConditions(next) {
      const replacement = snapshot(next);
      const id = selection()?.id;
      const found = replacement.findIndex((condition) => condition.id === id);
      const old = selection();
      conditions = replacement;
      selected =
        found < 0
          ? Math.min(selected, Math.max(0, conditions.length - 1))
          : found;
      const current = selection();
      if (
        current?.id !== old?.id ||
        current?.details !== old?.details ||
        current?.summary !== old?.summary
      )
        offset = 0;
      if (current === undefined) inspecting = false;
      requestRender();
    },
    setActivity(next) {
      activity = next === undefined ? undefined : { ...next };
      requestRender();
    },
    setFrame(next) {
      frame = next;
      if (
        activity?.state === ActivityState.Working &&
        options.presentation?.reducedMotion !== true
      )
        requestRender();
    },
    render(requestedWidth) {
      const width = allocation(requestedWidth);
      const height = allocation(options.height());
      if (width === 0 || height === 0) return [];
      const presentation = { ...options.presentation, frame };
      const heading = [
        theme.bold(statusText(options.title)),
        ...(activity === undefined
          ? []
          : [activityIndicator(activity, theme, presentation)]),
        ...(activity?.detail === undefined
          ? []
          : [theme.muted(statusText(activity.detail))]),
        ...wrapTextWithAnsi(
          theme.muted(conditionSummary(conditions, presentation)),
          width,
        ),
      ].map((line) => truncateToWidth(line, width));
      if (height <= heading.length) return heading.slice(0, height);
      const separator = presentation.ascii === true ? " - " : " · ";
      const position =
        conditions.length === 0
          ? []
          : [`${String(selected + 1)}/${String(conditions.length)}`];
      const help = theme.muted(
        (inspecting
          ? ["j/k scroll", "h back", "Esc back"]
          : [...position, "j/k select", "Enter inspect", "Esc close"]
        ).join(separator),
      );
      const bodyHeight = Math.max(0, height - heading.length - 1);
      page = Math.max(1, bodyHeight);
      const current = selection();
      let body: string[];
      if (current === undefined) {
        body = [theme.muted("No conditions supplied")].slice(0, bodyHeight);
      } else if (inspecting) {
        const lines = conditionDetails(current, theme, width, presentation);
        maximumOffset = Math.max(0, lines.length - bodyHeight);
        offset = Math.min(offset, maximumOffset);
        body = lines.slice(offset, offset + bodyHeight);
      } else {
        const split = width >= 76;
        const listWidth = split
          ? Math.min(48, Math.floor(width * 0.46))
          : width;
        const shown = Math.max(1, bodyHeight);
        first = Math.min(first, Math.max(0, conditions.length - shown));
        if (selected < first) first = selected;
        if (selected >= first + shown) first = selected - shown + 1;
        const labels = conditions
          .slice(first, first + shown)
          .map((condition, index) => {
            const active = activity?.focusId === condition.id;
            const marker = active
              ? theme.accent(options.presentation?.ascii === true ? "* " : "◆ ")
              : "";
            const status = conditionStatus(condition, theme, presentation);
            const available = Math.max(1, listWidth - visibleWidth(status) - 4);
            const label = fit(
              `${marker}${statusText(condition.label)}`,
              available,
            );
            const cursor =
              index + first === selected
                ? presentation.ascii === true
                  ? "> "
                  : "› "
                : "  ";
            const row = fit(`${cursor}${label}  ${status}`, listWidth);
            return index + first === selected ? theme.selected(row) : row;
          });
        if (split) {
          const detailWidth = width - listWidth - 3;
          const details = conditionDetails(
            current,
            theme,
            detailWidth,
            presentation,
          );
          body = Array.from(
            {
              length: Math.min(
                bodyHeight,
                Math.max(labels.length, details.length),
              ),
            },
            (_, index) =>
              `${fit(labels[index] ?? "", listWidth)}${theme.muted(presentation.ascii === true ? " | " : " │ ")}${details[index] ?? ""}`,
          );
        } else body = labels.slice(0, bodyHeight);
      }
      const remaining = Math.max(0, bodyHeight - body.length);
      return [
        ...heading,
        ...body,
        ...Array.from({ length: remaining }, () => ""),
        truncateToWidth(help, width),
      ].map((line) => truncateToWidth(line, width));
    },
    handleInput(input) {
      if (closed) return;
      if (matchesKey(input, NavigationKey.Cancel)) {
        close();
        return;
      }
      if (matchesKey(input, NavigationKey.Escape)) {
        if (inspecting) inspecting = false;
        else close();
      } else if (
        matchesKey(input, NavigationKey.Back) ||
        matchesKey(input, NavigationKey.Left)
      ) {
        inspecting = false;
      } else if (
        matchesKey(input, NavigationKey.Inspect) ||
        matchesKey(input, NavigationKey.Right) ||
        matchesKey(input, NavigationKey.Enter)
      ) {
        if (selection() !== undefined) inspecting = true;
      } else if (
        matchesKey(input, NavigationKey.Down) ||
        matchesKey(input, NavigationKey.VimDown)
      ) {
        if (inspecting) offset = Math.min(maximumOffset, offset + 1);
        else move(1);
      } else if (
        matchesKey(input, NavigationKey.Up) ||
        matchesKey(input, NavigationKey.VimUp)
      ) {
        if (inspecting) offset = Math.max(0, offset - 1);
        else move(-1);
      } else if (matchesKey(input, NavigationKey.PageDown)) {
        if (inspecting) offset = Math.min(maximumOffset, offset + page);
        else move(page);
      } else if (matchesKey(input, NavigationKey.PageUp)) {
        if (inspecting) offset = Math.max(0, offset - page);
        else move(-page);
      } else if (matchesKey(input, NavigationKey.Home)) {
        if (inspecting) offset = 0;
        else move(-conditions.length);
      } else if (matchesKey(input, NavigationKey.End)) {
        if (inspecting) offset = maximumOffset;
        else move(conditions.length);
      }
      requestRender();
    },
  };
}
