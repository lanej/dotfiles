//! Presentation of the single status row. Tab identities and attention come from Zellij.
use crate::{
    clipped,
    modules::right_side,
    plain, tab_name,
    theme::{background, foreground},
    State,
};
use unicode_width::UnicodeWidthStr;
use zellij_tile::prelude::*;

#[derive(Clone, Copy)]
pub(crate) struct Ribbon {
    pub(crate) fg: PaletteColor,
    pub(crate) bg: PaletteColor,
    pub(crate) bold: bool,
}

impl Ribbon {
    pub(crate) fn paint(self, text: &str) {
        print!(
            "\x1b[{};{};{}m{}",
            if self.bold { 1 } else { 22 },
            foreground(self.fg),
            background(self.bg),
            text
        );
    }
}

struct Tab {
    position: usize,
    name: String,
    mark: &'static str,
    zoom: &'static str,
    style: Ribbon,
}

impl Tab {
    fn width(&self) -> usize {
        // A space on either side, the tab number and colon, and the separator.
        self.name.width()
            + self.position.to_string().len()
            + 4
            + self.mark.width()
            + self.zoom.width()
    }

    fn draw(
        &self,
        budget: usize,
        previous: PaletteColor,
        edge: PaletteColor,
        ascii: bool,
    ) -> usize {
        if budget == 0 {
            return 0;
        }
        join(previous, self.style.bg, edge, ascii);
        if budget == 1 {
            return 1;
        }
        let fixed = self.width() - self.name.width();
        if budget < fixed {
            let position = clipped(&self.position.to_string(), budget - 1);
            self.style.paint(&position);
            return 1 + position.width();
        }
        let name = clipped(&self.name, budget - fixed);
        let label = format!(" {}{}{}:{} ", self.mark, self.zoom, self.position, name);
        self.style.paint(&label);
        label.width() + 1
    }
}

// A transition cell is both the preceding tab's point and the next tab's notch.
// Equal fills need an outlined chevron or their shared edge would disappear.
fn join(left: PaletteColor, right: PaletteColor, edge: PaletteColor, ascii: bool) {
    let equal = left == right;
    Ribbon {
        fg: if equal { edge } else { left },
        bg: right,
        bold: false,
    }
    .paint(if ascii {
        ">"
    } else if equal {
        ""
    } else {
        ""
    });
}

// Share the remaining cells between long names after accounting for the short ones.
fn width_limit(widths: &mut [usize], mut cells: usize) -> usize {
    widths.sort_unstable();
    for (i, width) in widths.iter().enumerate() {
        let share = cells / (widths.len() - i);
        if *width >= share {
            return share;
        }
        cells -= width;
    }
    widths.last().copied().unwrap_or_default()
}

fn counts(counts: &AttentionCounts) -> String {
    [
        ("!", counts.needs_you + counts.failed),
        ("●", counts.working),
        ("✓", counts.done),
    ]
    .into_iter()
    .filter(|(_, n)| *n > 0)
    .map(|(glyph, n)| format!("{glyph}{n}"))
    .collect::<Vec<_>>()
    .join(" ")
}

impl State {
    fn bar_tab(&self, tab: &TabInfo) -> Tab {
        use AttentionStatus::*;
        let colors = self.mode.style.colors;
        let surface = colors.text_unselected.background;
        let panes = self.panes.panes.get(&tab.position).into_iter().flatten();
        let mut kinds = panes
            .filter(|p| p.attention.effective_status() == NeedsYou)
            .filter_map(|p| p.attention.detail.kind);
        let status =
            if tab.has_bell_notification && !tab.attention.muted && tab.attention.status == Idle {
                NeedsYou
            } else {
                tab.attention.status
            };
        let mark = match status {
            NeedsYou if kinds.clone().any(|k| k == BlockedKind::Question) => "? ",
            NeedsYou if kinds.any(|k| k == BlockedKind::Permission) => "▲ ",
            NeedsYou => "! ",
            Failed => "× ",
            Done => "✓ ",
            Working => "● ",
            NewOutput => "· ",
            _ => "",
        };
        let style = match status {
            _ if tab.active => Ribbon {
                fg: colors.ribbon_selected.base,
                bg: if tab.is_fullscreen_active {
                    colors.text_unselected.emphasis_0
                } else {
                    colors.ribbon_selected.background
                },
                bold: true,
            },
            NeedsYou => Ribbon {
                fg: surface,
                bg: colors.ribbon_unselected.emphasis_0,
                bold: true,
            },
            Failed => Ribbon {
                fg: surface,
                bg: colors.exit_code_error.base,
                bold: true,
            },
            _ => Ribbon {
                fg: match status {
                    Working => colors.text_unselected.emphasis_1,
                    Done => colors.exit_code_success.base,
                    _ => colors.ribbon_unselected.base,
                },
                bg: colors.text_selected.background,
                bold: false,
            },
        };
        Tab {
            position: tab.position,
            name: if tab.active && self.mode.mode == InputMode::RenameTab {
                plain(&tab.name)
            } else {
                tab_name(tab, &self.panes)
            },
            mark,
            zoom: if !tab.is_fullscreen_active {
                ""
            } else if self.mode.capabilities.arrow_fonts {
                "Z "
            } else {
                "󰊓 "
            },
            style,
        }
    }

    pub(crate) fn render_bar(&mut self, cols: usize, dimmed: bool) {
        let colors = self.mode.style.colors;
        let surface = colors.text_unselected.background;
        let counts = if self.attention_ready {
            counts(&self.attention.counts)
        } else {
            "!? ●? ✓?".into()
        };
        let notification = self.notifications.notice();
        let notice_color = match notification.map(|(level, _)| level) {
            Some("error") => colors.exit_code_error.base,
            Some("warn") => colors.text_unselected.emphasis_0,
            Some("success") => colors.exit_code_success.base,
            _ => colors.ribbon_unselected.base,
        };
        let notice = self
            .clipboard
            .notice()
            .or_else(|| notification.map(|(_, text)| text));
        let mode = match self.mode.mode {
            InputMode::Normal | InputMode::Locked => "",
            InputMode::Tmux => "PREFIX ",
            InputMode::Resize => "RESIZE ",
            InputMode::Move => "MOVE ",
            InputMode::Tab => "TAB ",
            InputMode::RenameTab => "RENAME TAB ",
            InputMode::Scroll => "SCROLL ",
            InputMode::EnterSearch | InputMode::Search => "SEARCH ",
            _ => "MODE ",
        };
        let session = plain(self.mode.session_name.as_deref().unwrap_or(""));
        let heading_text = format!(" {mode}{session} ");
        let active = self.tabs.iter().position(|tab| tab.active).unwrap_or(0);
        let all_tabs: Vec<_> = self.tabs.iter().map(|t| self.bar_tab(t)).collect();
        let active_width = all_tabs.get(active).map_or(0, |tab| tab.width().min(32));
        let ideal_left = heading_text.width().min(30)
            + 1
            + all_tabs.iter().map(|t| t.width().min(32)).sum::<usize>();
        let compact_left = heading_text.width().min(14) + active_width + 12;
        let right = right_side(
            &self.view,
            &self.mode,
            &counts,
            notice.map(|s| (s, notice_color)),
            cols,
            ideal_left,
            compact_left,
        );
        let available = cols - right.width();
        let heading = clipped(
            &heading_text,
            available.saturating_sub(active_width.max(12) + 1).min(30),
        );
        let ascii = self.mode.capabilities.arrow_fonts;
        let accent = colors.text_unselected.emphasis_1;
        let edge = colors.ribbon_unselected.base;
        print!("\x1b[{}m", if dimmed { 3 } else { 23 });
        let mut used = 0;
        let mut previous = surface;
        if !heading.is_empty() {
            Ribbon {
                fg: surface,
                bg: accent,
                bold: true,
            }
            .paint(&heading);
            used = heading.width();
            previous = accent;
        }
        let tab_space = available.saturating_sub(used + 1);
        let active_budget = active_width.min(tab_space);
        let visible = (1 + tab_space.saturating_sub(active_budget) / 12).min(self.tabs.len());
        let end = (active.saturating_sub(visible / 2) + visible).min(self.tabs.len());
        let start = end - visible;
        let visible_tabs = &all_tabs[start..end];
        let mut other_widths: Vec<_> = visible_tabs
            .iter()
            .enumerate()
            .filter(|(i, _)| start + i != active)
            .map(|(_, tab)| tab.width())
            .collect();
        let limit = width_limit(&mut other_widths, tab_space - active_budget);
        let others_used: usize = other_widths.into_iter().map(|width| width.min(limit)).sum();
        for (i, tab) in visible_tabs.iter().enumerate() {
            let budget = if start + i == active {
                tab_space - others_used
            } else {
                limit
            };
            let width = tab.draw(budget, previous, edge, ascii);
            if width > 0 {
                self.clicks
                    .push((used, used + width, tab.position as u32 + 1));
                used += width;
                previous = tab.style.bg;
            }
        }
        if used > 0 && used < available {
            join(previous, surface, edge, ascii);
            used += 1;
            if let Some(last) = self.clicks.last_mut() {
                last.1 = used;
            }
        }
        Ribbon {
            fg: edge,
            bg: surface,
            bold: false,
        }
        .paint(&" ".repeat(available - used));
        right.draw(surface);
        print!("\x1b[0m");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selected_and_failed_tabs_take_their_colors_from_the_running_theme() {
        let mut state = State::default();
        let colors = &mut state.mode.style.colors;
        colors.ribbon_selected.base = PaletteColor::EightBit(17);
        colors.exit_code_error.base = PaletteColor::Rgb((11, 22, 33));
        let mut tab = TabInfo::default();
        tab.attention.status = AttentionStatus::Failed;
        assert_eq!(background(state.bar_tab(&tab).style.bg), "48;2;11;22;33");
        tab.active = true;
        assert_eq!(foreground(state.bar_tab(&tab).style.fg), "38;5;17");
        assert_eq!(state.bar_tab(&tab).mark.trim(), "×");
    }
}
