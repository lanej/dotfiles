import {
  matchesKey,
  truncateToWidth,
  wrapTextWithAnsi,
  type Component,
} from "@earendil-works/pi-tui";
import { selectorText } from "./text.ts";
import {
  ActivityState,
  activityIndicator,
  renderStatusMark,
  statusText,
  type Activity,
  type StatusPresentation,
  type StatusTheme,
} from "./status.ts";
import {
  boardRows,
  columnHeading,
  extent,
  fit,
  joinColumns,
  renderRow,
  summaryLine,
  type BoardRow,
  type StatusColumn,
} from "./status-dock.ts";

export interface StatusBoardOptions {
  title: string;
  initialColumnId?: string | undefined;
  columns: readonly StatusColumn[];
  theme: StatusTheme;
  height: () => number;
  requestRender: () => void;
  onClose?: (() => void) | undefined;
  activity?: Activity | undefined;
  presentation?: StatusPresentation | undefined;
}

export interface StatusSelection {
  columnId: string;
  groupId?: string | undefined;
  itemId?: string | undefined;
}

export interface StatusBoard extends Component {
  handleInput: (input: string) => void;
  setColumns: (columns: readonly StatusColumn[]) => void;
  setActivity: (activity: Activity | undefined) => void;
  setFrame: (frame: number) => void;
  selection: () => StatusSelection | undefined;
}

interface ColumnCursor {
  selected?: string | undefined;
  offset: number;
  folds: Map<string, boolean>;
}

function snapshotColumns(columns: readonly StatusColumn[]): StatusColumn[] {
  if (columns.length > 2)
    throw new RangeError("A status board supports one or two columns");
  const distinct = (ids: string[]) =>
    ids.every((id) => id.trim().length > 0) && new Set(ids).size === ids.length;
  if (!distinct(columns.map((column) => column.id)))
    throw new RangeError("Status columns require distinct nonempty IDs");
  for (const column of columns) {
    if (
      !distinct(column.groups.map((group) => group.id)) ||
      !distinct(
        column.groups.flatMap((group) => group.items.map((item) => item.id)),
      )
    )
      throw new RangeError(
        "Status groups and items require distinct nonempty IDs within each column",
      );
    if (
      column.counts?.some(
        (count) => !Number.isSafeInteger(count.value) || count.value < 0,
      ) === true
    )
      throw new RangeError("Status counts must be nonnegative safe integers");
  }
  return structuredClone([...columns]);
}

function cursorFor(
  cursors: Map<string, ColumnCursor>,
  column: StatusColumn,
): ColumnCursor {
  let cursor = cursors.get(column.id);
  if (cursor === undefined) {
    cursor = { offset: 0, folds: new Map() };
    cursors.set(column.id, cursor);
  }
  return cursor;
}

function selectionRow(
  rows: readonly BoardRow[],
  cursor: ColumnCursor,
): BoardRow | undefined {
  const found =
    rows.find((row) => row.focusable && row.key === cursor.selected) ??
    rows.find((row) => row.item !== undefined) ??
    rows.find((row) => row.focusable);
  cursor.selected = found?.key;
  return found;
}

function itemDetails(
  column: StatusColumn,
  row: BoardRow,
  width: number,
  theme: StatusTheme,
  presentation: StatusPresentation,
): string[] {
  const item = row.item;
  if (item === undefined) return [];
  const sections = [
    theme.muted(
      [statusText(column.title), statusText(row.group.label)].join(
        presentation.ascii === true ? " / " : " › ",
      ),
    ),
    `${theme.bold(statusText(item.label))}   ${renderStatusMark(item.status, theme, presentation)}`,
    ...(item.summary === undefined
      ? []
      : [theme.muted(selectorText(item.summary))]),
    ...(item.details === undefined ? [] : ["", selectorText(item.details)]),
  ];
  return wrapTextWithAnsi(sections.join("\n"), width);
}

export function createStatusBoard(options: StatusBoardOptions): StatusBoard {
  let columns = snapshotColumns(options.columns);
  if (
    options.initialColumnId !== undefined &&
    !columns.some((column) => column.id === options.initialColumnId)
  )
    throw new RangeError("Initial status column must be present");
  let currentId = options.initialColumnId ?? columns[0]?.id;
  let activity =
    options.activity === undefined ? undefined : { ...options.activity };
  let frame = options.presentation?.frame;
  const cursors = new Map<string, ColumnCursor>();
  let inspect = false;
  let help = false;
  let detailOffset = 0;
  let detailMaximum = 0;
  let pageSize = 1;
  let closed = false;
  const activeColumn = () => columns.find((column) => column.id === currentId);
  const getSelection = () => {
    const column = activeColumn();
    if (column === undefined) return undefined;
    const cursor = cursorFor(cursors, column);
    const rows = boardRows(column, cursor.folds);
    const row = selectionRow(rows, cursor);
    return { column, cursor, rows, row };
  };
  const close = () => {
    if (closed || options.onClose === undefined) return;
    closed = true;
    options.onClose();
  };
  const switchColumn = () => {
    const next = columns.find((column) => column.id !== currentId);
    if (next !== undefined) currentId = next.id;
    inspect = false;
    detailOffset = 0;
  };

  return {
    invalidate() {},
    selection() {
      const selected = getSelection();
      if (selected === undefined) return undefined;
      return {
        columnId: selected.column.id,
        groupId: selected.row?.group.id,
        itemId: selected.row?.item?.id,
      };
    },
    setColumns(next) {
      const replacement = snapshotColumns(next);
      const previous = getSelection();
      columns = replacement;
      if (!columns.some((column) => column.id === currentId))
        currentId = columns[0]?.id;
      for (const savedId of cursors.keys()) {
        if (!columns.some((column) => column.id === savedId))
          cursors.delete(savedId);
      }
      for (const column of columns) {
        const cursor = cursorFor(cursors, column);
        for (const key of cursor.folds.keys())
          if (
            !column.groups.some(
              (group) => group.id === key && group.collapsed !== undefined,
            )
          )
            cursor.folds.delete(key);
      }
      const selected = getSelection();
      if (
        selected?.column.id !== previous?.column.id ||
        selected?.row?.key !== previous?.row?.key
      ) {
        inspect = false;
        detailOffset = 0;
      } else if (selected?.row?.item?.details !== previous?.row?.item?.details)
        detailOffset = 0;
      options.requestRender();
    },
    setActivity(next) {
      activity = next === undefined ? undefined : { ...next };
      options.requestRender();
    },
    setFrame(next) {
      frame = next;
      if (
        activity?.state === ActivityState.Working &&
        options.presentation?.reducedMotion !== true
      )
        options.requestRender();
    },
    render(requestedWidth) {
      const width = extent(requestedWidth);
      const height = extent(options.height());
      if (width === 0 || height === 0) return [];
      const { theme } = options;
      const presentation = { ...options.presentation, frame };
      const selected = getSelection();
      const title = theme.bold(statusText(options.title));
      const header =
        activity === undefined
          ? title
          : `${title}   ${activityIndicator(activity, theme, { ...presentation, compact: true })}`;
      const hint = help
        ? inspect
          ? "j/k scroll · PgUp/PgDn page · Esc back"
          : "Tab/h/l column · j/k row · Enter inspect/fold · Esc close"
        : inspect
          ? "Esc back  ·  ? keys"
          : "? keys";
      const footer = theme.muted(
        presentation.ascii === true ? hint.replaceAll("·", "-") : hint,
      );
      const bodyHeight = Math.max(0, height - 2);
      let body: string[] = [];
      if (selected === undefined) body = [theme.muted("No columns")];
      else if (inspect && selected.row?.item !== undefined) {
        const detail = itemDetails(
          selected.column,
          selected.row,
          width,
          theme,
          presentation,
        );
        pageSize = Math.max(1, bodyHeight);
        detailMaximum = Math.max(0, detail.length - pageSize);
        detailOffset = Math.min(detailOffset, detailMaximum);
        body = detail.slice(detailOffset, detailOffset + pageSize);
      } else {
        const content = (
          column: StatusColumn,
          allocation: number,
          available: number,
        ) => {
          const cursor = cursorFor(cursors, column);
          const rows = boardRows(column, cursor.folds);
          const chosen = selectionRow(rows, cursor);
          const index = chosen === undefined ? 0 : rows.indexOf(chosen);
          const position = Math.min(
            cursor.offset,
            Math.max(0, rows.length - available),
          );
          cursor.offset = Math.max(
            0,
            Math.min(index, Math.max(position, index - available + 1)),
          );
          if (column.id === currentId) pageSize = Math.max(1, available);
          if (rows.length === 0)
            return [
              theme.muted(statusText(column.emptyMessage ?? "No items")),
            ].slice(0, available);
          return rows
            .slice(cursor.offset, cursor.offset + available)
            .map((row) =>
              renderRow(
                row,
                column,
                allocation,
                theme,
                presentation,
                column.id === currentId && row.key === cursor.selected,
              ),
            );
        };
        const first = columns[0];
        const second = columns[1];
        if (first !== undefined && second !== undefined && width >= 76) {
          const leftWidth = Math.floor((width - 3) / 2);
          const rightWidth = width - leftWidth - 3;
          const leftHead = columnHeading(
            first,
            leftWidth,
            theme,
            presentation,
            first.id === currentId,
          );
          const rightHead = columnHeading(
            second,
            rightWidth,
            theme,
            presentation,
            second.id === currentId,
          );
          const heading = joinColumns(
            leftHead,
            rightHead,
            leftWidth,
            width,
            theme,
            presentation,
          );
          const remaining = Math.max(0, bodyHeight - heading.length - 1);
          body = [
            ...heading,
            "",
            ...joinColumns(
              content(first, leftWidth, remaining),
              content(second, rightWidth, remaining),
              leftWidth,
              width,
              theme,
              presentation,
            ),
          ];
        } else {
          const tabs = columns.map((column) => {
            const focused = column.id === currentId;
            const label = summaryLine(column, width - 2, theme, presentation);
            const prefix = focused
              ? presentation.ascii === true
                ? "> "
                : "› "
              : "  ";
            return focused
              ? theme.selected(fit(prefix + label, width))
              : prefix + label;
          });
          const summary = selected.column.summary;
          if (summary !== undefined)
            tabs.push(theme.muted(statusText(summary)));
          const remaining = Math.max(0, bodyHeight - tabs.length - 1);
          body = [...tabs, "", ...content(selected.column, width, remaining)];
        }
      }
      return [
        header,
        ...body.slice(0, bodyHeight),
        ...(body.length < bodyHeight ? [""] : []),
        footer,
      ]
        .slice(0, height)
        .map((line) => truncateToWidth(line, width));
    },
    handleInput(input) {
      if (closed) return;
      const selected = getSelection();
      const down = matchesKey(input, "down") || input === "j";
      const up = matchesKey(input, "up") || input === "k";
      const pageDown = matchesKey(input, "pageDown");
      const pageUp = matchesKey(input, "pageUp");
      const home = matchesKey(input, "home");
      const end = matchesKey(input, "end");
      if (matchesKey(input, "ctrl+c")) close();
      else if (input === "?") help = !help;
      else if (inspect) {
        if (
          matchesKey(input, "escape") ||
          input === "h" ||
          matchesKey(input, "left")
        )
          inspect = false;
        else if (down || pageDown || end)
          detailOffset = Math.min(
            detailMaximum,
            end ? detailMaximum : detailOffset + (pageDown ? pageSize : 1),
          );
        else if (up || pageUp || home)
          detailOffset = Math.max(
            0,
            home ? 0 : detailOffset - (pageUp ? pageSize : 1),
          );
      } else if (matchesKey(input, "escape")) close();
      else if (
        matchesKey(input, "tab") ||
        matchesKey(input, "shift+tab") ||
        matchesKey(input, "left") ||
        matchesKey(input, "right") ||
        input === "h" ||
        input === "l"
      )
        switchColumn();
      else if (selected !== undefined) {
        const { cursor, rows, row } = selected;
        if (matchesKey(input, "enter") && row !== undefined) {
          if (row.item !== undefined) {
            inspect = true;
            detailOffset = 0;
          } else cursor.folds.set(row.group.id, !row.folded);
        } else if (down || up || pageDown || pageUp || home || end) {
          const choices = rows.filter((entry) => entry.focusable);
          const at = row === undefined ? 0 : choices.indexOf(row);
          const next = home
            ? 0
            : end
              ? choices.length - 1
              : at +
                (up || pageUp ? -1 : 1) * (pageDown || pageUp ? pageSize : 1);
          cursor.selected =
            choices[Math.min(Math.max(0, next), choices.length - 1)]?.key;
        }
      }
      options.requestRender();
    },
  };
}
