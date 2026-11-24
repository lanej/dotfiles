import { selectorText } from "./text.ts";

export enum ConditionState {
  Unknown = "unknown",
  Satisfied = "satisfied",
  Partial = "partial",
  Open = "open",
  NotApplicable = "not-applicable",
}

export interface Condition {
  readonly id: string;
  readonly label: string;
  readonly state: ConditionState;
  readonly summary?: string | undefined;
  readonly details?: string | undefined;
  /** The saved assessment needs rechecking; its evidence remains inspectable. */
  readonly stale?: boolean | undefined;
}

export enum ActivityState {
  Idle = "idle",
  Working = "working",
  Waiting = "waiting",
  Paused = "paused",
}

export interface Activity {
  readonly state: ActivityState;
  readonly label: string;
  readonly detail?: string | undefined;
  /** The caller identifies the current subject; this never changes selection. */
  readonly focusId?: string | undefined;
}

export interface StatusTheme {
  accent: (text: string) => string;
  muted: (text: string) => string;
  bold: (text: string) => string;
  success: (text: string) => string;
  warning: (text: string) => string;
  error: (text: string) => string;
  selected: (text: string) => string;
}

export interface StatusPresentation {
  /** Animation is host-driven; omitting a frame gives a static working mark. */
  readonly frame?: number | undefined;
  readonly reducedMotion?: boolean | undefined;
  readonly ascii?: boolean | undefined;
  /** Use the supplied activity label without repeating the generic state word. */
  readonly compact?: boolean | undefined;
}

interface Appearance {
  glyph: string;
  ascii: string;
  label: string;
  tone: "accent" | "muted" | "success" | "warning";
}

const conditionAppearance = {
  [ConditionState.Unknown]: {
    glyph: "○",
    ascii: "?",
    label: "Not assessed",
    tone: "muted",
  },
  [ConditionState.Satisfied]: {
    glyph: "●",
    ascii: "+",
    label: "Satisfied",
    tone: "success",
  },
  [ConditionState.Open]: {
    glyph: "○",
    ascii: "!",
    label: "Open",
    tone: "warning",
  },
  [ConditionState.Partial]: {
    glyph: "◐",
    ascii: "~",
    label: "Partial",
    tone: "warning",
  },
  [ConditionState.NotApplicable]: {
    glyph: "−",
    ascii: "-",
    label: "Not applicable",
    tone: "muted",
  },
} satisfies Record<ConditionState, Appearance>;

const staleAppearance: Appearance = {
  glyph: "↺",
  ascii: "~",
  label: "Recheck",
  tone: "warning",
};

const activityAppearance = {
  [ActivityState.Idle]: {
    glyph: "○",
    ascii: "-",
    label: "Idle",
    tone: "muted",
  },
  [ActivityState.Working]: {
    glyph: "◐",
    ascii: "*",
    label: "Working",
    tone: "accent",
  },
  [ActivityState.Waiting]: {
    glyph: "◷",
    ascii: "?",
    label: "Waiting",
    tone: "warning",
  },
  [ActivityState.Paused]: {
    glyph: "‖",
    ascii: "|",
    label: "Paused",
    tone: "muted",
  },
} satisfies Record<ActivityState, Appearance>;

const activityFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
const asciiFrames = ["|", "/", "-", "\\"];

export function statusText(value: string): string {
  return selectorText(value).replace(/\s+/gu, " ").trim();
}

export function conditionStatus(
  condition: Condition,
  theme: StatusTheme,
  presentation: StatusPresentation = {},
): string {
  return renderStatusMark(conditionMark(condition), theme, presentation);
}

export function conditionMark(
  condition: Pick<Condition, "state" | "stale">,
): StatusMark {
  return {
    ...(condition.stale === true
      ? staleAppearance
      : conditionAppearance[condition.state]),
  };
}

export function activityIndicator(
  activity: Activity,
  theme: StatusTheme,
  presentation: StatusPresentation = {},
): string {
  const appearance = activityAppearance[activity.state];
  let glyph = presentation.ascii === true ? appearance.ascii : appearance.glyph;
  if (
    activity.state === ActivityState.Working &&
    presentation.reducedMotion !== true &&
    presentation.frame !== undefined &&
    Number.isFinite(presentation.frame)
  ) {
    const frames = presentation.ascii === true ? asciiFrames : activityFrames;
    glyph =
      frames[Math.abs(Math.trunc(presentation.frame)) % frames.length] ?? glyph;
  }
  const label = statusText(activity.label);
  const separator = presentation.ascii === true ? " - " : " · ";
  return theme[appearance.tone](
    presentation.compact === true && label.length > 0
      ? `${glyph} ${label}`
      : `${glyph} ${appearance.label}${label.length === 0 ? "" : separator + label}`,
  );
}

export type StatusTone = "muted" | "accent" | "success" | "warning" | "error";

export interface StatusMark {
  readonly label: string;
  readonly glyph: string;
  readonly ascii?: string | undefined;
  readonly tone: StatusTone;
}

export interface StatusCount {
  readonly label: string;
  readonly value: number;
  readonly tone: StatusTone;
}

export function renderStatusMark(
  mark: StatusMark,
  theme: StatusTheme,
  presentation: StatusPresentation = {},
): string {
  const glyph = statusText(
    presentation.ascii === true ? (mark.ascii ?? "*") : mark.glyph,
  );
  return theme[mark.tone](`${glyph} ${statusText(mark.label)}`.trim());
}

export function renderStatusCounts(
  counts: readonly StatusCount[],
  theme: StatusTheme,
  presentation: StatusPresentation = {},
): string {
  return counts
    .map((count) => {
      if (!Number.isSafeInteger(count.value) || count.value < 0)
        throw new RangeError("Status counts must be nonnegative safe integers");
      return theme[count.tone](
        `${theme.bold(String(count.value))} ${statusText(count.label)}`,
      );
    })
    .join(theme.muted(presentation.ascii === true ? " - " : " · "));
}

export interface ConditionCounts {
  total: number;
  satisfied: number;
  partial: number;
  open: number;
  unknown: number;
  notApplicable: number;
  stale: number;
}

export function conditionCounts(
  conditions: readonly Condition[],
): ConditionCounts {
  const counts: ConditionCounts = {
    total: conditions.length,
    satisfied: 0,
    partial: 0,
    open: 0,
    unknown: 0,
    notApplicable: 0,
    stale: 0,
  };
  for (const condition of conditions) {
    if (condition.stale === true) {
      counts.stale++;
      continue;
    }
    switch (condition.state) {
      case ConditionState.Satisfied:
        counts.satisfied++;
        break;
      case ConditionState.Open:
        counts.open++;
        break;
      case ConditionState.Partial:
        counts.partial++;
        break;
      case ConditionState.Unknown:
        counts.unknown++;
        break;
      case ConditionState.NotApplicable:
        counts.notApplicable++;
        break;
    }
  }
  return counts;
}

export function conditionSummary(
  conditions: readonly Condition[],
  presentation: StatusPresentation = {},
): string {
  const counts = conditionCounts(conditions);
  if (counts.total === 0) return "No conditions supplied";
  return [
    `${String(counts.satisfied)} satisfied`,
    counts.partial === 0 ? "" : `${String(counts.partial)} partial`,
    counts.open === 0 ? "" : `${String(counts.open)} open`,
    counts.unknown === 0 ? "" : `${String(counts.unknown)} not assessed`,
    counts.stale === 0 ? "" : `${String(counts.stale)} to recheck`,
    counts.notApplicable === 0
      ? ""
      : `${String(counts.notApplicable)} not applicable`,
  ]
    .filter((part) => part.length > 0)
    .join(presentation.ascii === true ? " - " : " · ");
}
