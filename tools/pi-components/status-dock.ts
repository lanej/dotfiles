import { truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";
import {
  renderStatusCounts,
  renderStatusMark,
  statusText,
  type StatusCount,
  type StatusMark,
  type StatusPresentation,
  type StatusTheme,
  type StatusTone,
} from "./status.ts";

export interface StatusItem {
  readonly id: string;
  readonly label: string;
  readonly status: StatusMark;
  readonly summary?: string | undefined;
  readonly details?: string | undefined;
}

export interface StatusGroup {
  readonly id: string;
  readonly label: string;
  readonly items: readonly StatusItem[];
  /** Omit repeated labels when the group already names their shared state. */
  readonly showStatusLabels?: boolean | undefined;
  /** A boolean enables folding with this initial state; omitted groups stay open. */
  readonly collapsed?: boolean | undefined;
  readonly tone?: StatusTone | undefined;
}

export interface StatusColumn {
  readonly id: string;
  readonly title: string;
  readonly status?: StatusMark | undefined;
  readonly summary?: string | undefined;
  readonly counts?: readonly StatusCount[] | undefined;
  readonly groups: readonly StatusGroup[];
  readonly emptyMessage?: string | undefined;
  /** Current subject supplied by the host, independent of keyboard selection. */
  readonly focusId?: string | undefined;
}

export interface StatusDockOptions {
  columns: readonly StatusColumn[];
  theme: StatusTheme;
  width: number;
  expanded: boolean;
  /** Hard row limit. Defaults to eight expanded, or content-sized when compact. */
  maxRows?: number | undefined;
  presentation?: StatusPresentation | undefined;
}

export function extent(value: number): number {
  return Number.isFinite(value) ? Math.max(0, Math.trunc(value)) : 0;
}

export function fit(value: string, width: number): string {
  if (width <= 0) return "";
  const line = truncateToWidth(value, width);
  return line + " ".repeat(Math.max(0, width - visibleWidth(line)));
}

function columnTitle(
  column: StatusColumn,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
  selected = false,
): string {
  const title = theme.bold(statusText(column.title));
  const state =
    column.status === undefined
      ? ""
      : renderStatusMark(column.status, theme, presentation);
  const gap = Math.max(2, width - visibleWidth(title) - visibleWidth(state));
  const line =
    state.length === 0 ? title : `${title}${" ".repeat(gap)}${state}`;
  return selected ? theme.selected(fit(line, width)) : fit(line, width);
}

export function columnHeading(
  column: StatusColumn,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
  selected = false,
): string[] {
  return [
    columnTitle(column, width, theme, presentation, selected),
    ...((column.counts?.length ?? 0) > 0
      ? [
          truncateToWidth(
            renderStatusCounts(column.counts ?? [], theme, presentation),
            width,
          ),
        ]
      : []),
    ...(column.summary === undefined || column.summary.trim().length === 0
      ? []
      : [theme.muted(truncateToWidth(statusText(column.summary), width))]),
  ];
}

function itemRow(
  item: StatusItem,
  group: StatusGroup,
  column: StatusColumn,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
  selected = false,
): string {
  const glyph = theme[item.status.tone](
    statusText(
      presentation.ascii === true
        ? (item.status.ascii ?? "*")
        : item.status.glyph,
    ),
  );
  const focus =
    column.focusId === item.id
      ? theme.accent(presentation.ascii === true ? " *" : " ◆")
      : "";
  const cursor = selected ? (presentation.ascii === true ? "> " : "› ") : "  ";
  const label = `${cursor}${glyph} ${statusText(item.label)}`;
  const state =
    group.showStatusLabels === false
      ? ""
      : theme[item.status.tone](statusText(item.status.label));
  const summary =
    item.summary === undefined ? "" : theme.muted(statusText(item.summary));
  // The current status and subject outrank secondary IDs at narrow widths.
  const summaryBudget = Math.max(
    0,
    width -
      Math.min(18, visibleWidth(label)) -
      visibleWidth(state) -
      visibleWidth(focus) -
      4,
  );
  const suffix = [
    summaryBudget > 3 ? truncateToWidth(summary, summaryBudget) : "",
    state,
  ]
    .filter((part) => part.length > 0)
    .join("  ");
  const labelWidth = Math.max(
    1,
    width -
      visibleWidth(suffix) -
      visibleWidth(focus) -
      (suffix.length > 0 ? 2 : 0),
  );
  const row =
    suffix.length === 0
      ? `${truncateToWidth(label, labelWidth)}${focus}`
      : `${fit(`${truncateToWidth(label, labelWidth)}${focus}`, labelWidth + visibleWidth(focus))}  ${suffix}`;
  return selected ? theme.selected(fit(row, width)) : fit(row, width);
}

export interface BoardRow {
  group: StatusGroup;
  item?: StatusItem | undefined;
  key: string;
  focusable: boolean;
  folded: boolean;
}

export function boardRows(
  column: StatusColumn,
  folds?: ReadonlyMap<string, boolean>,
): BoardRow[] {
  const rows: BoardRow[] = [];
  for (const group of column.groups) {
    if (group.items.length === 0) continue;
    const foldable = group.collapsed !== undefined;
    const folded = foldable && (folds?.get(group.id) ?? group.collapsed);
    rows.push({ group, key: `group:${group.id}`, focusable: foldable, folded });
    if (folded) continue;
    for (const item of group.items)
      rows.push({
        group,
        item,
        key: `item:${item.id}`,
        focusable: true,
        folded: false,
      });
  }
  return rows;
}

export function renderRow(
  row: BoardRow,
  column: StatusColumn,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
  selected: boolean,
): string {
  if (row.item !== undefined)
    return itemRow(
      row.item,
      row.group,
      column,
      width,
      theme,
      presentation,
      selected,
    );
  const group = row.group;
  const fold =
    group.collapsed === undefined
      ? ""
      : row.folded
        ? presentation.ascii === true
          ? "> "
          : "▸ "
        : presentation.ascii === true
          ? "v "
          : "▾ ";
  const cursor = selected ? (presentation.ascii === true ? "> " : "› ") : "";
  const count =
    group.collapsed === undefined ? "" : ` ${String(group.items.length)}`;
  const text = theme[group.tone ?? "muted"](
    `${cursor}${fold}${statusText(group.label)}${count}`,
  );
  return selected
    ? theme.selected(fit(text, width))
    : truncateToWidth(text, width);
}

export function summaryLine(
  column: StatusColumn,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
): string {
  const mark =
    column.status === undefined
      ? ""
      : renderStatusMark(column.status, theme, presentation);
  const counts = renderStatusCounts(column.counts ?? [], theme, presentation);
  return truncateToWidth(
    [theme.bold(statusText(column.title)), mark, counts]
      .filter((part) => part.length > 0)
      .join("  "),
    width,
  );
}

function dockRows(
  column: StatusColumn,
  width: number,
  height: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
): string[] {
  const rows = boardRows(column);
  if (height <= 0) return [];
  if (rows.length === 0)
    return [
      truncateToWidth(
        theme.muted(statusText(column.emptyMessage ?? "No items")),
        width,
      ),
    ];
  const render = (row: BoardRow) =>
    renderRow(row, column, width, theme, presentation, false);
  if (rows.length <= height) return rows.map(render);
  // Narrow excerpts make room for actual work first. Groups the caller folded stay folded.
  const actionable = rows.filter((row) => row.item !== undefined);
  const folded = rows.filter((row) => row.folded);
  const first = actionable[0];
  const focused = actionable.find((row) => row.item?.id === column.focusId);
  const ordered =
    focused === undefined
      ? actionable
      : [focused, ...actionable.filter((row) => row !== focused)];
  const excerpt: string[] = [];
  if (
    height >= 4 &&
    first !== undefined &&
    first.group.collapsed === undefined &&
    (focused === undefined || focused.group.id === first.group.id)
  )
    excerpt.push(
      theme[first.group.tone ?? "muted"](statusText(first.group.label)),
    );
  const spare = height - excerpt.length;
  const n = Math.min(
    ordered.length,
    Math.max(1, spare - (spare > 2 && ordered.length > spare ? 1 : 0)),
  );
  excerpt.push(...ordered.slice(0, n).map(render));
  const fold = folded[0];
  const visibleFold = fold !== undefined && excerpt.length < height;
  if (visibleFold) excerpt.push(render(fold));
  const omitted =
    ordered.length -
    n +
    folded
      .slice(visibleFold ? 1 : 0)
      .reduce((sum, row) => sum + row.group.items.length, 0);
  if (omitted > 0 && excerpt.length < height)
    excerpt.push(theme.muted(`+${String(omitted)} more`));
  return excerpt;
}

export function joinColumns(
  left: string[],
  right: string[],
  leftWidth: number,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
): string[] {
  const divider = theme.muted(presentation.ascii === true ? " | " : " │ ");
  return Array.from(
    { length: Math.max(left.length, right.length) },
    (_, index) =>
      truncateToWidth(
        `${fit(left[index] ?? "", leftWidth)}${divider}${right[index] ?? ""}`,
        width,
      ),
  );
}

/** A read-only, bounded surface. Mount it in the host's existing layout without taking focus. */
export function renderStatusDock(options: StatusDockOptions): string[] {
  const { columns, theme } = options;
  const width = extent(options.width);
  const presentation = options.presentation ?? {};
  const limit = extent(options.maxRows ?? (options.expanded ? 8 : 3));
  if (width === 0 || limit === 0 || columns.length === 0) return [];
  if (columns.length > 2)
    throw new RangeError("A status dock supports one or two columns");
  const first = columns[0];
  if (first === undefined) return [];
  const second = columns[1];
  const render = (column: StatusColumn, allocation: number): string[] => {
    const heading = columnHeading(column, allocation, theme, presentation);
    return options.expanded
      ? [
          ...heading,
          ...dockRows(
            column,
            allocation,
            limit - heading.length,
            theme,
            presentation,
          ),
        ]
      : heading;
  };
  let lines: string[];
  if (second === undefined) lines = render(first, width);
  else if (width >= 72) {
    const leftWidth = Math.floor((width - 3) / 2);
    lines = joinColumns(
      render(first, leftWidth),
      render(second, width - leftWidth - 3),
      leftWidth,
      width,
      theme,
      presentation,
    );
  } else if (!options.expanded) {
    lines = columns.map((column) =>
      summaryLine(column, width, theme, presentation),
    );
    const summary = columns.find(
      (column) => (column.summary?.trim().length ?? 0) > 0,
    )?.summary;
    if (summary !== undefined) lines.push(theme.muted(statusText(summary)));
  } else {
    const firstHeight = Math.ceil(limit / 2);
    const section = (column: StatusColumn, height: number) => [
      summaryLine(column, width, theme, presentation),
      ...dockRows(column, width, height - 1, theme, presentation),
    ];
    lines = [
      ...section(first, firstHeight),
      ...section(second, limit - firstHeight),
    ];
  }
  return lines.slice(0, limit).map((line) => truncateToWidth(line, width));
}
