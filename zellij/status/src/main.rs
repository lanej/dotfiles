use serde_json::{json, Value};
use std::collections::BTreeMap;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};
use zellij_tile::prelude::*;

#[derive(Default)]
struct State {
    mode: ModeInfo,
    tabs: Vec<TabInfo>,
    panes: PaneManifest,
    view: Value,
    allowed: bool,
    visible: bool,
    busy: bool,
    attention: GlobalAttention,
    attention_ready: bool,
    clicks: Vec<(usize, usize, u32)>,
}

register_plugin!(State);

fn plain(value: &str) -> String {
    value.chars().filter(|c| !c.is_control()).collect()
}

fn clipped(value: &str, budget: usize) -> String {
    if value.width() <= budget { return value.to_owned(); }
    let mut text = String::new();
    let mut used = 0;
    for c in value.chars() {
        let width = c.width().unwrap_or(0);
        if used + width + 1 > budget { break; }
        text.push(c); used += width;
    }
    if budget > 0 { text.push('…'); }
    text
}

fn mark(status: AttentionStatus, question: bool) -> (&'static str, &'static str) {
    match status {
        AttentionStatus::NeedsYou if question => ("?", "235;203;139"),
        AttentionStatus::NeedsYou => ("!", "235;203;139"),
        AttentionStatus::Failed => ("×", "191;97;106"),
        AttentionStatus::Done => ("✓", "163;190;140"),
        AttentionStatus::Working => ("●", "136;192;208"),
        AttentionStatus::NewOutput => ("·", "136;192;208"),
        _ => ("", "136;192;208"),
    }
}

impl State {
    fn poll(&mut self) {
        if !self.allowed || self.busy || !self.visible { return; }
        // Native Zellij owns attention, including detached sessions. The
        // helper supplies only host metadata; no external sampler is needed.
        run_command(&["zellij-status", "view"], BTreeMap::new());
        self.busy = true;
    }
}

impl ZellijPlugin for State {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        self.visible = true;
        subscribe(&[EventType::ModeUpdate, EventType::TabUpdate, EventType::PaneUpdate,
            EventType::RunCommandResult, EventType::Timer, EventType::PermissionRequestResult,
            EventType::Visible, EventType::Mouse, EventType::SessionUpdate,
            EventType::GlobalAttentionUpdate]);
        request_permission(&[PermissionType::ReadApplicationState,
            PermissionType::RunCommands, PermissionType::ChangeApplicationState]);
        set_timeout(1.0);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                // 0.45.1 can replay another client's cached grant while this
                // instance still lacks permissions. Changing selectability
                // requests a state broadcast; only a granted instance can
                // receive SessionUpdate and safely make synchronous queries.
                set_selectable(false);
            }
            Event::SessionUpdate(..) if !self.allowed => {
                self.allowed = true;
                self.poll();
            }
            Event::ModeUpdate(mode) => { self.mode = mode; self.poll(); }
            Event::TabUpdate(tabs) => { self.tabs = tabs; }
            Event::GlobalAttentionUpdate(attention) => {
                self.attention = attention;
                self.attention_ready = true;
            }
            Event::PaneUpdate(panes) => { self.panes = panes; }
            Event::Visible(visible) => { self.visible = visible; if visible { self.poll(); } }
            Event::Timer(_) => { self.poll(); set_timeout(1.0); }
            Event::RunCommandResult(code, out, error, _) => {
                self.busy = false;
                self.view = if code == Some(0) {
                    serde_json::from_slice(&out).unwrap_or(json!({"available": false}))
                } else {
                    eprintln!("lane-status helper failed: {}", String::from_utf8_lossy(&error));
                    json!({"available": false})
                };
            }
            Event::Mouse(Mouse::LeftClick(_, col)) if self.allowed => {
                if let Some((_, _, index)) = self.clicks.iter().find(|(start, end, _)| col >= *start && col < *end) {
                    switch_tab_to(*index);
                }
            }
            _ => {}
        }
        true
    }

    fn render(&mut self, _rows: usize, cols: usize) {
        self.clicks.clear();
        if !self.allowed {
            print!("Grant lane-status permissions to enable the top bar");
            return;
        }
        let attention = self.attention.counts.needs_you + self.attention.counts.failed
            + self.attention.counts.done;
        let working = self.attention.counts.working;
        let clock = plain(self.view["clock"].as_str().unwrap_or(""));
        let battery = plain(self.view["battery"].as_str().unwrap_or(""));
        let counts = if self.attention_ready {
            format!("!{} ●{}", attention, working)
        } else { "!? ●?".into() };
        let right = format!(" {} {} {} ", counts, battery, clock);
        let right_width = right.width().min(cols);
        let available = cols.saturating_sub(right_width);
        let host = plain(self.view["host"].as_str().unwrap_or(""));
        let prefix = if self.mode.mode != InputMode::Locked && self.mode.mode != InputMode::Normal { " PREFIX " } else { " " };
        let mut used = 0;
        // Match the native tab bar's host/guest focus signal. A dimmed session
        // is still visible, but its keys currently belong to another session.
        let dimmed = self.mode.session_ascended == Some(true)
            || self.mode.session_dimmed == Some(true);
        print!("\x1b[{}m", if dimmed { 3 } else { 23 });
        print!("\x1b[48;2;46;52;64m\x1b[38;2;136;192;208m");
        let heading = format!("{}{} │", prefix, host);
        for c in heading.chars() {
            let width = c.width().unwrap_or(0);
            if used + width > available { break; }
            print!("{}", c); used += width;
        }
        let tab_space = available.saturating_sub(used);
        let visible = (tab_space / 12).max(1).min(self.tabs.len());
        let active = self.tabs.iter().position(|t| t.active).unwrap_or(0);
        let end = (active.saturating_sub(visible / 2) + visible).min(self.tabs.len());
        let start = end.saturating_sub(visible);
        let budget = if visible > 0 { (tab_space / visible).min(32) } else { 0 };
        for tab in &self.tabs[start..end] {
            let question = self.panes.panes.get(&tab.position).into_iter().flatten()
                .any(|pane| pane.attention.effective_status() == AttentionStatus::NeedsYou
                    && pane.attention.detail.kind == Some(BlockedKind::Question));
            let (glyph, color) = if tab.attention.status == AttentionStatus::Idle && tab.has_bell_notification {
                ("!", "235;203;139")
            } else { mark(tab.attention.status, question) };
            let zoom = if tab.is_fullscreen_active { " Z" } else { "" };
            let name_budget = budget.saturating_sub(tab.position.to_string().len() + 5 + zoom.len());
            let name = clipped(&plain(&tab.name), name_budget);
            let label = format!(" {}:{} {}{} ", tab.position, name, glyph, zoom);
            let start = used;
            print!("\x1b[48;2;{}m\x1b[38;2;{}m", if tab.active { "76;65;82" } else { "46;52;64" }, if tab.active && glyph.is_empty() { "180;142;173" } else { color });
            for c in label.chars() {
                let width = c.width().unwrap_or(0);
                if used + width > available { break; }
                print!("{}", c); used += width;
            }
            if used > start { self.clicks.push((start, used, tab.position as u32 + 1)); }
            if used >= available { break; }
        }
        print!("\x1b[48;2;46;52;64m{}\x1b[38;2;129;161;193m", " ".repeat(available.saturating_sub(used)));
        let mut right_used = 0;
        for c in right.chars() {
            let width = c.width().unwrap_or(0);
            if right_used + width > right_width { break; }
            print!("{}", c); right_used += width;
        }
        print!("\x1b[0m");
    }
}
