//! Render read-only pane snapshots. Only SGR styles enter fzf, never OSC or cursor commands.
use crate::util::*;
use anyhow::{Context, Result};
use serde_json::Value;
use std::collections::BTreeMap;
use std::env;
use unicode_width::UnicodeWidthChar;
#[derive(Clone, Default)]
struct Cell {
    text: String,
    style: Vec<u16>,
}
fn cell(text: &str) -> Cell {
    Cell {
        text: text.into(),
        style: vec![],
    }
}
fn style(styles: &mut BTreeMap<u16, Vec<u16>>, parameters: &str) -> Vec<u16> {
    let codes: Vec<u16> = parameters
        .split(';')
        .map(|s| s.parse().unwrap_or(0))
        .collect();
    let mut index = 0;
    while index < codes.len() {
        let code = codes[index];
        index += 1;
        let resets: &[u16] = match code {
            22 => &[1, 2],
            23 => &[3],
            24 => &[4, 21],
            25 => &[5, 6],
            27 => &[7],
            28 => &[8],
            29 => &[9],
            39 => &[38],
            49 => &[48],
            59 => &[58],
            _ => &[],
        };
        if code == 0 {
            styles.clear();
        } else if !resets.is_empty() {
            for key in resets {
                styles.remove(key);
            }
        } else if matches!(code, 38 | 48 | 58) {
            let Some(mode) = codes.get(index) else {
                break;
            };
            let count = match mode {
                2 => 4,
                5 => 2,
                _ => break,
            };
            if index + count > codes.len() {
                break;
            }
            let mut value = vec![code];
            value.extend_from_slice(&codes[index..index + count]);
            styles.insert(code, value);
            index += count;
        } else if (30..=37).contains(&code) || (90..=97).contains(&code) {
            styles.insert(38, vec![code]);
        } else if (40..=47).contains(&code) || (100..=107).contains(&code) {
            styles.insert(48, vec![code]);
        } else if (1..=9).contains(&code) || code == 21 {
            styles.insert(code, vec![code]);
        }
    }
    styles.values().flatten().copied().collect()
}
fn screen_rows(text: &str, width: usize, ansi: bool) -> Result<Vec<Vec<Cell>>> {
    let width = width.max(1);
    let mut rows = vec![];
    let mut cells: Vec<Cell> = vec![];
    let mut styles = BTreeMap::new();
    let mut active = vec![];
    let tokens =
        regex::Regex::new(r"(?s)\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\n|.")?;
    let sgr = regex::Regex::new(r"^\x1b\[([0-9;]*)m$")?;
    for token in tokens.find_iter(text) {
        let token = token.as_str();
        if token.starts_with('\x1b') {
            if ansi {
                if let Some(capture) = sgr.captures(token) {
                    active = style(&mut styles, &capture[1]);
                }
            }
            continue;
        }
        if token == "\n" {
            cells.resize(width, cell(" "));
            rows.push(std::mem::take(&mut cells));
            continue;
        }
        let c = token.chars().next().context("Empty token")?;
        let c = if printable(c) { c } else { ' ' };
        let size = c.width().unwrap_or(1);
        if size == 0 {
            let index = if cells.last().is_some_and(|c| c.text.is_empty()) {
                cells.len().checked_sub(2)
            } else {
                cells.len().checked_sub(1)
            };
            if let Some(i) = index {
                cells[i].text.push(c);
            }
            continue;
        }
        let (c, size) = if size > width { ('?', 1) } else { (c, size) };
        if cells.len() + size > width {
            cells.resize(width, cell(" "));
            rows.push(std::mem::take(&mut cells));
        }
        cells.push(Cell {
            text: c.to_string(),
            style: active.clone(),
        });
        if size == 2 {
            cells.push(Cell::default());
        }
    }
    if !cells.is_empty() || rows.is_empty() {
        cells.resize(width, cell(" "));
        rows.push(cells);
    }
    Ok(rows)
}
fn render(rows: &[Vec<Cell>]) -> String {
    rows.iter()
        .map(|row| {
            let mut active = vec![];
            let mut line = String::new();
            for cell in row {
                if cell.text.is_empty() {
                    continue;
                }
                if cell.style != active {
                    line += "\x1b[0m";
                    if !cell.style.is_empty() {
                        line += &format!(
                            "\x1b[{}m",
                            cell.style
                                .iter()
                                .map(u16::to_string)
                                .collect::<Vec<_>>()
                                .join(";")
                        );
                    }
                    active = cell.style.clone();
                }
                line += &cell.text;
            }
            line + "\x1b[0m"
        })
        .collect::<Vec<_>>()
        .join("\n")
}
fn pane_title(pane: &Value) -> Result<String> {
    let title = label(pane["title"].as_str().unwrap_or(""));
    let pattern = regex::Regex::new(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F-]+(?:\.{3}|…)?")?;
    Ok(pattern
        .replace_all(&title, "")
        .split('|')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join(" | "))
}
fn pane_screen(connection: &crate::picker::PickerSession, pane: &Value) -> Result<String> {
    Ok(connection
        .action(
            crate::ipc::contract::action::ActionType::DumpScreen(
                crate::ipc::contract::DumpScreenAction {
                    pane_id: Some(crate::ipc::contract::PaneId {
                        pane_type: Some(crate::ipc::contract::pane_id::PaneType::Terminal(
                            number(pane, "id")?.try_into()?,
                        )),
                    }),
                    dump_to_stdout: true,
                    ansi: true,
                    ..Default::default()
                },
            ),
            true,
        )
        .unwrap_or_else(|e| format!("Preview unavailable: {}", label(&e.to_string())))
        .trim_end()
        .to_owned())
}
fn dimension(name: &str, default: usize) -> usize {
    env::var(name)
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(default)
        .clamp(1, 4096)
}
pub fn tab(session: &str, tab_id: u64) -> Result<()> {
    let connection = crate::picker::PickerSession::resolve(session)?;
    let own = if env::var("ZELLIJ_SESSION_NAME").as_deref() == Ok(session) {
        pane_id().ok()
    } else {
        None
    };
    let mut panes: Vec<_> = connection
        .panes(false)?
        .into_iter()
        .filter(|p| {
            p["tab_id"] == tab_id
                && !flag(p, "is_plugin")
                && !flag(p, "is_suppressed")
                && p["id"].as_u64() != own
        })
        .collect();
    if panes.is_empty() {
        println!("No other terminal pane in this tab.");
        return Ok(());
    }
    let tabs = connection.tabs()?;
    let Some(tab) = tabs.iter().find(|t| t["tab_id"] == tab_id) else {
        println!("Tab closed while loading preview.");
        return Ok(());
    };
    panes.retain(|p| !flag(p, "is_floating") || flag(tab, "are_floating_panes_visible"));
    let fullscreen = panes.iter().any(|p| flag(p, "is_fullscreen"));
    panes.retain(|p| !fullscreen || flag(p, "is_fullscreen") || flag(p, "is_floating"));
    if panes.is_empty() {
        println!("No visible terminal pane in this tab.");
        return Ok(());
    }
    let width = dimension("FZF_PREVIEW_COLUMNS", 100);
    let height = dimension("FZF_PREVIEW_LINES", 30);
    let rects: Vec<_> = panes
        .iter()
        .map(|p| {
            Ok((
                number(p, "pane_x")?,
                number(p, "pane_y")?,
                number(p, "pane_columns")?,
                number(p, "pane_rows")?,
            ))
        })
        .collect::<Result<_>>()?;
    let left = rects.iter().map(|r| r.0).min().context("No panes")?;
    let top = rects.iter().map(|r| r.1).min().context("No panes")?;
    let span_x = rects
        .iter()
        .map(|r| r.0.saturating_add(r.2))
        .max()
        .context("No panes")?
        .saturating_sub(left)
        .max(1);
    let span_y = rects
        .iter()
        .map(|r| r.1.saturating_add(r.3))
        .max()
        .context("No panes")?
        .saturating_sub(top)
        .max(1);
    let scale = |value: u64, size: usize, span: u64| {
        ((value as f64 * size as f64 / span as f64).round_ties_even() as usize).min(size)
    };
    let mut rectangles: Vec<_> = panes
        .iter()
        .zip(rects)
        .map(|(p, (x, y, w, h))| {
            (
                p,
                scale(x - left, width, span_x),
                scale(y - top, height, span_y),
                scale(x.saturating_add(w) - left, width, span_x),
                scale(y.saturating_add(h) - top, height, span_y),
            )
        })
        .collect();
    if rectangles
        .iter()
        .any(|(_, x, y, r, b)| r.saturating_sub(*x) < 4 || b.saturating_sub(*y) < 4)
    {
        let mut rows = vec![];
        let per_pane = (height / panes.len()).max(1);
        panes.sort_by_key(|p| (p["pane_y"].as_u64(), p["pane_x"].as_u64()));
        for p in &panes {
            rows.push(
                screen_rows(
                    &format!("{}: {}", number(p, "id")?, pane_title(p)?),
                    width,
                    false,
                )?
                .remove(0),
            );
            if per_pane > 1 {
                let lines = screen_rows(&pane_screen(&connection, p)?, width, true)?;
                rows.extend_from_slice(&lines[lines.len().saturating_sub(per_pane - 1)..]);
            }
        }
        if rows.len() > height {
            rows.truncate(height - 1);
            rows.push(screen_rows("More panes; enlarge preview", width, false)?.remove(0));
        }
        println!("{}", render(&rows));
        return Ok(());
    }
    let mut canvas = vec![vec![cell(" "); width]; height];
    rectangles.sort_by_key(|(p, ..)| (flag(p, "is_floating"), p["id"].as_u64()));
    for (p, x, y, right, bottom) in rectangles {
        let inner = right - x - 2;
        for row in canvas.iter_mut().take(bottom).skip(y) {
            if row[x].text.is_empty() && x > 0 {
                row[x - 1] = cell(" ");
            }
            if right < width && row[right].text.is_empty() {
                row[right] = cell(" ");
            }
            row[x..right].fill(cell(" "));
            row[x] = cell("│");
            row[right - 1] = cell("│");
        }
        canvas[y][x..right].fill(cell("─"));
        canvas[y][x] = cell("┌");
        canvas[y][right - 1] = cell("┐");
        canvas[bottom - 1][x..right].fill(cell("─"));
        canvas[bottom - 1][x] = cell("└");
        canvas[bottom - 1][right - 1] = cell("┘");
        let title = format!(
            " {}{}: {} ",
            if flag(p, "is_focused") { "*" } else { "" },
            number(p, "id")?,
            pane_title(p)?
        );
        canvas[y][x + 1..right - 1].clone_from_slice(&screen_rows(&title, inner, false)?[0]);
        let command = label(
            p["pane_command"]
                .as_str()
                .filter(|s| !s.is_empty())
                .unwrap_or("terminal"),
        );
        let cwd = std::path::Path::new(p["pane_cwd"].as_str().unwrap_or(""))
            .file_name()
            .unwrap_or_default()
            .to_string_lossy();
        canvas[y + 1][x + 1..right - 1]
            .clone_from_slice(&screen_rows(&format!("{command} | {cwd}"), inner, false)?[0]);
        let mut rows = screen_rows(&pane_screen(&connection, p)?, inner, true)?;
        let available = bottom - y - 3;
        if rows.len() > available {
            let tail = if available > 1 {
                rows.split_off(rows.len() - available + 1)
            } else {
                vec![]
            };
            rows = vec![screen_rows("↑ earlier screen lines", inner, false)?.remove(0)];
            rows.extend(tail);
        }
        for (i, row) in rows.iter().take(available).enumerate() {
            canvas[y + 2 + i][x + 1..right - 1].clone_from_slice(row);
        }
    }
    println!("{}", render(&canvas));
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn previews_preserve_cells_and_styles_but_strip_terminal_commands() {
        let rows = screen_rows("\x1b]52;c;payload\x07\x1b[31m界e\u{301}\x1b[2J!", 4, true).unwrap();
        assert_eq!(rows.len(), 1);
        assert_eq!(rows[0][0].text, "界");
        assert_eq!(rows[0][1].text, "");
        assert_eq!(rows[0][2].text, "e\u{301}");
        let rendered = render(&rows);
        assert!(rendered.contains("\x1b[31m"));
        assert!(!rendered.contains("payload"));
        assert!(!rendered.contains("\x1b[2J"));
    }
}
