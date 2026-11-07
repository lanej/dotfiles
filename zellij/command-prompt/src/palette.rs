use crate::{
    commands,
    completion::{self, Context, Suggestion},
};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use zellij_tile::prelude::*;

pub const REPLY: &str = "command-palette-submit";

#[derive(Serialize, Deserialize)]
pub struct Open {
    pub owner: u32,
    pub client: ClientId,
    pub request: u64,
    pub origin: (usize, PaneId),
    pub line: String,
    pub history: Vec<String>,
    pub error: String,
}

#[derive(Serialize, Deserialize)]
pub struct Reply {
    pub request: u64,
    pub client: ClientId,
    pub line: String,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum View {
    Command,
    Help,
    History,
    Panes,
    Tabs,
    Sessions,
    Documentation,
}

pub struct Palette {
    open: Open,
    input: TextInput,
    view: View,
    context: Context,
    selected: usize,
    history_at: Option<usize>,
    draft: String,
    error: String,
    documentation: String,
    scroll: usize,
    allowed: bool,
}

impl Palette {
    pub fn new(open: Open) -> Self {
        Self {
            input: TextInput::new(&open.line).label(":").focused(),
            error: open.error.clone(),
            open,
            view: View::Command,
            context: Context::default(),
            selected: 0,
            history_at: None,
            draft: String::new(),
            documentation: String::new(),
            scroll: 0,
            allowed: false,
        }
    }

    pub fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                if get_plugin_ids().client_id != self.open.client {
                    return false;
                }
                self.allowed = true;
                self.refresh();
                true
            }
            Event::Key(key) if self.allowed => self.key(key),
            Event::PastedText(text) if self.allowed && self.view != View::Documentation => {
                for c in text.chars() {
                    if matches!(c, '\n' | '\r' | '\t') {
                        self.input.insert_char(' ');
                    } else if !c.is_control() {
                        self.input.insert_char(c);
                    }
                }
                self.selected = 0;
                self.error.clear();
                true
            }
            Event::PaneUpdate(_) | Event::TabUpdate(_) | Event::SessionUpdate(..)
                if self.allowed =>
            {
                self.refresh();
                true
            }
            _ => false,
        }
    }

    fn refresh(&mut self) {
        if let Ok(snapshot) = get_session_list() {
            if let Some(session) = snapshot.live_sessions.iter().find(|s| s.is_current_session) {
                self.context.tabs = session.tabs.clone();
                self.context.tabs.sort_by_key(|t| t.position);
                self.context.panes = session
                    .panes
                    .panes
                    .iter()
                    .flat_map(|(tab, panes)| panes.iter().map(move |p| (*tab, p.clone())))
                    .collect();
                self.context.panes.sort_by_key(|(tab, p)| (*tab, p.id));
                self.context.session_name = session.name.clone();
                self.context.tab_name = session
                    .tabs
                    .iter()
                    .find(|t| t.tab_id == self.open.origin.0)
                    .map(|t| t.name.clone())
                    .unwrap_or_default();
                self.context.pane_name = get_pane_info(self.open.origin.1)
                    .map(|p| p.title)
                    .unwrap_or_default();
            }
            self.context.sessions = snapshot.live_sessions;
            self.context.sessions.sort_by(|a, b| a.name.cmp(&b.name));
        }
        self.selected = self.selected.min(self.items().len().saturating_sub(1));
    }

    fn items(&self) -> Vec<Suggestion> {
        if self.view == View::Command {
            return completion::complete(
                self.input.get_text(),
                self.input.cursor_position(),
                &self.context,
                &self.open.history,
            )
            .items;
        }
        let items = match self.view {
            View::Help => completion::complete("", 0, &self.context, &self.open.history).items,
            View::History => self
                .open
                .history
                .iter()
                .map(|line| Suggestion::new(line, line, "recent command"))
                .collect(),
            View::Panes => completion::pane_targets(&self.context),
            View::Tabs => completion::tab_targets(&self.context, true),
            View::Sessions => completion::session_targets(&self.context),
            _ => vec![],
        };
        items
            .into_iter()
            .filter(|item| {
                completion::matches(
                    self.input.get_text(),
                    &format!("{} {}", item.label, item.detail),
                )
            })
            .collect()
    }

    fn select(&mut self, delta: isize) {
        let count = self.items().len();
        if count > 0 {
            self.selected = (self.selected as isize + delta).rem_euclid(count as isize) as usize;
        }
    }

    fn recall(&mut self, older: bool) {
        if self.view != View::Command || self.open.history.is_empty() {
            return;
        }
        if self.history_at.is_none() {
            self.draft = self.input.get_text().into();
        }
        self.history_at = match (self.history_at, older) {
            (None, true) => Some(0),
            (Some(i), true) => Some((i + 1).min(self.open.history.len() - 1)),
            (Some(0), false) => None,
            (Some(i), false) => Some(i - 1),
            (None, false) => None,
        };
        self.input.set_text(
            self.history_at
                .map(|i| self.open.history[i].as_str())
                .unwrap_or(&self.draft),
        );
        self.selected = 0;
        self.error.clear();
    }

    fn back(&mut self) {
        self.view = View::Command;
        self.input = TextInput::new(&self.open.line).label(":").focused();
        self.selected = 0;
        self.error.clear();
    }

    fn complete(&mut self) {
        let items = self.items();
        let Some(item) = items.get(self.selected) else {
            return;
        };
        if self.view != View::Command {
            self.activate();
            return;
        }
        let line = self.input.get_text();
        let completed = completion::complete(
            line,
            self.input.cursor_position(),
            &self.context,
            &self.open.history,
        );
        let value = if completed.command {
            item.value.clone()
        } else {
            completion::quote(&item.value)
        };
        let end = completed.replace.start + value.len();
        let append_space = completed.command && completed.replace.end == line.len();
        let line = format!(
            "{}{}{}{}",
            &line[..completed.replace.start],
            value,
            if append_space { " " } else { "" },
            &line[completed.replace.end..]
        );
        let cursor = line[..end].chars().count() + usize::from(append_space);
        self.input.set_text(line);
        self.input.set_cursor_position(cursor);
        self.selected = 0;
        self.history_at = None;
        self.error.clear();
    }

    fn key(&mut self, key: KeyWithModifier) -> bool {
        let plain = key.has_no_modifiers();
        let ctrl = |c| key.bare_key == BareKey::Char(c) && key.has_modifiers(&[KeyModifier::Ctrl]);
        if (plain && key.bare_key == BareKey::Esc) || ctrl('c') {
            if self.view == View::Command {
                close_self();
            } else {
                self.back();
            }
        } else if ctrl('p') {
            self.recall(true);
        } else if ctrl('n') {
            self.recall(false);
        } else if ctrl('r') {
            self.show(View::History);
        } else if plain && key.bare_key == BareKey::Up {
            if self.history_at.is_some() || (self.input.is_empty() && self.view == View::Command) {
                self.recall(true);
            } else if self.view == View::Documentation {
                self.scroll = self.scroll.saturating_sub(1);
            } else {
                self.select(-1);
            }
        } else if plain && key.bare_key == BareKey::Down {
            if self.history_at.is_some() {
                self.recall(false);
            } else if self.view == View::Documentation {
                self.scroll += 1;
            } else {
                self.select(1);
            }
        } else if plain && key.bare_key == BareKey::Tab {
            self.complete();
        } else if plain && key.bare_key == BareKey::Enter {
            self.activate();
        } else if self.view != View::Documentation {
            self.input.handle_key(&key);
            self.selected = 0;
            self.history_at = None;
            self.error.clear();
        }
        true
    }

    fn show(&mut self, view: View) {
        if self.view == View::Command {
            self.open.line = self.input.get_text().into();
        }
        self.view = view;
        self.input = TextInput::empty().label("filter").focused();
        self.selected = 0;
        self.error.clear();
        self.refresh();
    }

    fn activate(&mut self) {
        if self.view == View::Documentation {
            self.back();
            return;
        }
        if self.view != View::Command {
            let items = self.items();
            let Some(item) = items.get(self.selected) else {
                return;
            };
            match self.view {
                View::Help | View::History => {
                    let line = format!(
                        "{}{}",
                        item.value,
                        if self.view == View::Help { " " } else { "" }
                    );
                    self.back();
                    self.input.set_text(line);
                }
                View::Panes => self.submit(format!("focus-pane-id {}", item.value)),
                View::Tabs => self.submit(format!("go-to-tab-by-id {}", item.value)),
                View::Sessions => {
                    self.submit(format!("switch-session {}", completion::quote(&item.value)))
                }
                _ => {}
            }
            return;
        }
        let line = self
            .input
            .get_text()
            .trim()
            .trim_start_matches(':')
            .to_owned();
        match line.as_str() {
            "" => close_self(),
            "help" => self.show(View::Help),
            "history" => self.show(View::History),
            "list-panes" => self.show(View::Panes),
            "list-tabs" => self.show(View::Tabs),
            "list-sessions" => self.show(View::Sessions),
            _ => match crate::parse(&line, std::path::PathBuf::from(".")) {
                Ok(crate::Parsed::Native(commands::Parsed::Help(help))) => {
                    self.open.line = self.input.get_text().into();
                    self.documentation = help;
                    self.view = View::Documentation;
                    self.scroll = 0;
                }
                Ok(_) => self.submit(line),
                Err(error) => self.error = error,
            },
        }
    }

    fn submit(&self, line: String) {
        let reply = Reply {
            request: self.open.request,
            client: self.open.client,
            line,
        };
        pipe_message_to_plugin(MessageToPlugin {
            destination_plugin_id: Some(self.open.owner),
            message_name: REPLY.into(),
            message_payload: Some(serde_json::to_string(&reply).expect("serializable reply")),
            ..Default::default()
        });
        close_self();
    }

    pub fn render(&mut self, rows: usize, columns: usize) {
        if !self.allowed || rows < 5 || columns < 12 {
            return;
        }
        print!("\u{1b}[2J\u{1b}[H");
        let width = columns.saturating_sub(4);
        let put =
            |row, value: Text| print_text_with_coordinates(value, 2, row, Some(width), Some(1));
        let title = match self.view {
            View::Command => "Zellij command :",
            View::Help => "Zellij commands",
            View::History => "Zellij command history",
            View::Panes => "Zellij command · panes",
            View::Tabs => "Zellij command · tabs",
            View::Sessions => "Zellij command · sessions",
            View::Documentation => "Zellij command · help",
        };
        put(1, Text::from(title).color_range(0, ..));
        let tab = self
            .context
            .tabs
            .iter()
            .find(|t| t.tab_id == self.open.origin.0);
        put(
            2,
            Text::from(sanitize_display_text(&format!(
                "{}  ·  tab {}: {}  ·  {}",
                self.context.session_name,
                tab.map(|t| t.position).unwrap_or(0),
                self.context.tab_name,
                self.context.pane_name
            )))
            .dim_range(..),
        );
        if self.view == View::Documentation {
            let lines: Vec<_> = self.documentation.lines().collect();
            self.scroll = self
                .scroll
                .min(lines.len().saturating_sub(rows.saturating_sub(6)));
            for (i, line) in lines
                .iter()
                .skip(self.scroll)
                .take(rows.saturating_sub(6))
                .enumerate()
            {
                put(i + 4, Text::from(*line));
            }
            put(
                rows - 1,
                Text::from("↑↓ scroll  ·  Enter/Esc back").dim_range(..),
            );
            return;
        }
        self.input.render(2, 4, width);
        let help = if self.error.is_empty() {
            if self.view == View::Command {
                completion::complete(
                    self.input.get_text(),
                    self.input.cursor_position(),
                    &self.context,
                    &self.open.history,
                )
                .help
            } else {
                "Filter by name or details. Enter selects; Esc returns to your command.".into()
            }
        } else {
            self.error.lines().take(2).collect::<Vec<_>>().join(" ")
        };
        put(
            6,
            if self.error.is_empty() {
                Text::from(help).dim_range(..)
            } else {
                Text::from(help).color_range(3, ..)
            },
        );
        let items = self.items();
        let visible = rows.saturating_sub(11).max(1);
        self.selected = self.selected.min(items.len().saturating_sub(1));
        let start = self.selected.saturating_sub(visible - 1);
        let mut table = Table::new().add_styled_row(vec![
            Text::from(match self.view {
                View::Panes => "PANE / TITLE",
                View::Tabs => "TAB / NAME",
                View::Sessions => "SESSION",
                _ => "COMMAND / VALUE",
            })
            .color_range(0, ..),
            Text::from("DETAILS").color_range(0, ..),
        ]);
        for (i, item) in items.iter().enumerate().skip(start).take(visible) {
            let label = sanitize_display_text(&item.label);
            let detail = sanitize_display_text(&item.detail);
            let cells = [label, detail]
                .into_iter()
                .map(|v| {
                    let value = Text::from(v);
                    if i == self.selected {
                        value.selected()
                    } else {
                        value
                    }
                })
                .collect();
            table = table.add_styled_row(cells);
        }
        print_table_with_coordinates(table, 2, 8, Some(width), Some(visible + 1));
        if items.is_empty() {
            put(9, Text::from("No matches").dim_range(..));
        }
        put(
            rows.saturating_sub(2),
            Text::from(format!("{} suggestions", items.len())).dim_range(..),
        );
        put(
            rows - 1,
            Text::from(if self.view == View::Command {
                "Tab complete  ·  ↑↓ select  ·  Enter run  ·  Ctrl-p/n history  ·  Esc close"
            } else {
                "↑↓ select  ·  Enter choose  ·  Esc back"
            })
            .dim_range(..),
        );
    }
}

pub fn launch(open: Open) {
    let tab = get_tab_info(open.origin.0).unwrap_or_default();
    let width = tab.display_area_columns.saturating_sub(4).clamp(12, 104);
    let height = tab.display_area_rows.saturating_sub(4).clamp(5, 24);
    let configuration = BTreeMap::from([(
        "palette".into(),
        serde_json::to_string(&open).expect("serializable popup"),
    )]);
    open_plugin_popup_with_options(
        "command-prompt",
        configuration,
        tab.display_area_rows.saturating_sub(height) / 2,
        tab.display_area_columns.saturating_sub(width) / 2,
        width,
        height,
        PopupOptions::default()
            .capture_all_keys(true)
            .outside_click(OutsideClick::Close),
    );
}

#[cfg(test)]
mod tests {
    use super::*;

    fn editor(line: &str) -> Palette {
        Palette::new(Open {
            owner: 1,
            client: 1,
            request: 1,
            origin: (0, PaneId::Terminal(1)),
            line: line.into(),
            history: vec!["rename-tab work".into(), "move-focus right".into()],
            error: String::new(),
        })
    }

    #[test]
    fn completing_a_quoted_name_preserves_the_rest_of_the_command() {
        let mut palette = editor("rename-tab \"dé\" --help");
        palette.context.tab_name = "déploy 'green'".into();
        palette.input.set_cursor_position(14);
        palette.complete();
        assert_eq!(
            shlex::split(palette.input.get_text()).unwrap(),
            ["rename-tab", "déploy 'green'", "--help"]
        );
    }

    #[test]
    fn history_round_trip_restores_the_unsubmitted_draft() {
        let mut palette = editor("rename-tab \"unsaved draft\"");
        palette.recall(true);
        assert_eq!(palette.input.get_text(), "rename-tab work");
        palette.recall(true);
        assert_eq!(palette.input.get_text(), "move-focus right");
        palette.recall(false);
        palette.recall(false);
        assert_eq!(palette.input.get_text(), "rename-tab \"unsaved draft\"");
    }

    #[test]
    fn invalid_argument_keeps_the_editable_line() {
        let mut palette = editor("move-focus sideways");
        palette.activate();
        assert!(!palette.error.is_empty());
        assert_eq!(palette.input.get_text(), "move-focus sideways");
        assert!(palette.view == View::Command);
    }
}
