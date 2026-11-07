use serde_json::{json, Value};
use std::collections::BTreeMap;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};
use zellij_tile::prelude::*;
mod clipboard;
mod attention;
mod clients;

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
    clipboard: clipboard::Clipboard,
    clipboard_receiver: bool,
    clipboard_prepared: bool,
    permissions_requested: bool,
    clients: clients::Clients,
}

register_plugin!(State);

fn leader(panes: &PaneManifest) -> u32 {
    panes.panes.values().flatten()
        .filter(|pane| pane.is_plugin && !pane.exited && !pane.is_suppressed
            && pane.plugin_url.as_deref().map(|url| url.ends_with("/lane-status.wasm")).unwrap_or(false))
        .map(|pane| pane.id).min().unwrap_or_else(|| get_plugin_ids().plugin_id)
}

fn plain(value: &str) -> String {
    value.chars().filter(|c| !c.is_control()).collect()
}

fn tab_name(tab: &TabInfo, panes: &PaneManifest, own_pane: Option<&PaneInfo>, owned: &Value) -> String {
    // Native defaults use a stable ID + 1, not the tab's current position.
    // Render a shell/application title without renaming the actual tab, so a
    // manual tab name and explicit pane titles retain native ownership.
    if tab.name != format!("Tab #{}", tab.tab_id + 1)
        && owned[tab.tab_id.to_string()].as_str() != Some(tab.name.as_str()) {
        return plain(&tab.name);
    }
    // PaneUpdate focus is aggregated and cached. The client snapshot supplies
    // its fresh native PaneInfo; tab-wide views require unambiguous focus.
    let eligible = |pane: &PaneInfo| !pane.is_plugin && !pane.is_floating
        && !pane.is_suppressed && !pane.exited;
    let mut focused = panes.panes.get(&tab.position).into_iter().flatten()
        .filter(|pane| eligible(pane) && pane.is_focused);
    let pane = match own_pane {
        Some(pane) => Some(pane).filter(|pane| eligible(pane)),
        None => focused.next().filter(|_| focused.next().is_none()),
    };
    if let Some(pane) = pane {
        let title = plain(&pane.title);
        let generated = title.strip_prefix("Pane #")
            .map(|number| !number.is_empty() && number.bytes().all(|b| b.is_ascii_digit()))
            .unwrap_or(false);
        if !title.is_empty() && !generated { return title; }
    }
    format!("Tab #{}", tab.position)
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
        if self.clipboard_receiver || !self.allowed || self.busy || !self.visible { return; }
        // Native Zellij owns attention, including detached sessions. The
        // helper supplies host metadata and lifecycle-checked title ownership.
        let Some(session) = self.mode.session_name.as_deref() else { return };
        run_command(&["zellij-status", "view", session], BTreeMap::new());
        self.busy = true;
    }
}

fn request_permissions() {
    request_permission(&[PermissionType::ReadApplicationState,
        PermissionType::RunCommands, PermissionType::ChangeApplicationState,
        PermissionType::WriteToStdin, PermissionType::Reconfigure,
        PermissionType::MessageAndLaunchOtherPlugins, PermissionType::ReadCliPipes]);
}

fn subscribe_events() {
    subscribe(&[EventType::ModeUpdate, EventType::TabUpdate, EventType::PaneUpdate,
        EventType::RunCommandResult, EventType::Timer, EventType::PermissionRequestResult,
        EventType::Visible, EventType::Mouse, EventType::InitialKeybinds,
        EventType::SessionUpdate, EventType::GlobalAttentionUpdate, EventType::ListClients]);
}

impl ZellijPlugin for State {
    fn load(&mut self, configuration: BTreeMap<String, String>) {
        self.clipboard_receiver = configuration.get("role").map(String::as_str) == Some(clipboard::ROLE);
        self.visible = true;
        // Only the visible bar asks for first-use consent. The suppressed
        // receiver waits for that bar to confirm its native permission grant.
        if !self.clipboard_receiver {
            self.clients.start();
            subscribe_events();
            request_permissions();
            self.permissions_requested = true;
        } else {
            subscribe(&[EventType::PermissionRequestResult]);
        }
        set_timeout(1.0);
    }

    fn update(&mut self, event: Event) -> bool {
        let bindings_changed = matches!(&event, Event::InitialKeybinds(..));
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                if self.clipboard_receiver { subscribe_events(); }
                // 0.45.1 can replay another client's cached grant while this
                // instance still lacks permissions. Changing selectability
                // requests a state broadcast; only a granted instance can
                // receive SessionUpdate and safely make synchronous queries.
                set_selectable(false);
            }
            Event::SessionUpdate(sessions, _) => {
                // Newly attached clones can receive ModeInfo without a name.
                // Native session metadata identifies their current session.
                let session = sessions.iter().find(|session| session.is_current_session)
                    .map(|session| session.name.clone());
                if self.mode.session_name != session { self.view = json!({}); }
                self.mode.session_name = session;
                if !self.allowed {
                    self.allowed = true;
                    self.poll();
                }
            }
            Event::ListClients(_) if self.allowed && !self.clipboard_receiver => self.clients.finish(),
            Event::ModeUpdate(mut mode) => {
                if mode.session_name.is_none() { mode.session_name = self.mode.session_name.clone(); }
                if self.mode.session_name != mode.session_name { self.view = json!({}); }
                self.mode = mode; self.poll();
            }
            Event::TabUpdate(tabs) => { self.tabs = tabs; }
            Event::GlobalAttentionUpdate(attention) => {
                self.attention = attention;
                self.attention_ready = true;
            }
            Event::PaneUpdate(panes) => { self.panes = panes; }
            Event::Visible(visible) => { self.visible = visible; if visible { self.poll(); } }
            Event::Timer(_) => { self.clipboard.tick(); self.poll(); set_timeout(1.0); }
            Event::RunCommandResult(code, out, error, context)
                if context.get("action").map(String::as_str) == Some(clipboard::MESSAGE) => {
                // Native client-attach replay can broadcast cached results.
                if context.get("client") == Some(&get_plugin_ids().client_id.to_string()) {
                    self.clipboard.finish(code, out, error);
                }
            }
            Event::RunCommandResult(code, out, error, _) => {
                self.busy = false;
                self.view = if code == Some(0) {
                    let view: Value = serde_json::from_slice(&out).unwrap_or(json!({}));
                    if view["session"].as_str() == self.mode.session_name.as_deref() { view }
                    else { json!({}) }
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
        if self.allowed {
            if self.clipboard_receiver {
                self.clipboard.route_bindings(bindings_changed);
            } else if !self.clipboard_prepared {
                self.clipboard_prepared = clipboard::prepare_receiver(&self.panes);
            }
        }
        !self.clipboard_receiver
    }

    fn pipe(&mut self, message: PipeMessage) -> bool {
        if self.allowed && !self.clipboard_receiver && matches!(message.source, PipeSource::Cli(_)) {
            return self.clients.pipe(&message, &self.panes);
        }
        if matches!(message.source, PipeSource::Plugin(_)) {
            if self.clipboard_receiver && message.is_private && !self.permissions_requested
                && message.name == clipboard::PREPARE && clipboard::is_own_client(&message)
            {
                // The bar sends this only after a permitted SessionUpdate.
                // Both roles use the same URL and permission set, so native
                // request_permission now applies the already-consented cache.
                request_permissions();
                self.permissions_requested = true;
            } else if !self.clipboard_receiver && self.allowed && message.name == clipboard::NOTICE {
                return self.clipboard.receive_notice(&message);
            }
        }
        if self.clipboard_receiver && self.allowed && message.source == PipeSource::Keybind
            && message.name == attention::MESSAGE {
            attention::jump(&self.tabs, &self.attention, &message);
        }
        if self.clipboard_receiver && self.allowed && message.source == PipeSource::Keybind && message.name == clipboard::MESSAGE {
            if let Some(session) = self.mode.session_name.as_deref() {
                return self.clipboard.begin(session, &message);
            }
        }
        false
    }

    fn render(&mut self, _rows: usize, cols: usize) {
        if self.clipboard_receiver { return; }
        self.clicks.clear();
        if !self.allowed {
            print!("Grant lane-status permissions to enable the top bar");
            return;
        }
        // Match the native tab bar's host/guest focus signal. A dimmed session
        // is still visible, but its keys currently belong to another session.
        let dimmed = self.mode.session_ascended == Some(true)
            || self.mode.session_dimmed == Some(true);
        if self.mode.mode == InputMode::Tmux && !dimmed {
            // Prefix waiting owns the whole row, even when a narrow terminal
            // would otherwise give all its space to the clock or a notice.
            let label = clipped(" PREFIX  waiting for next key  |  Esc cancels ", cols);
            print!("\x1b[1;23;48;2;180;142;173m\x1b[38;2;46;52;64m{}{}\x1b[0m",
                label, " ".repeat(cols.saturating_sub(label.width())));
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
        let right = if let Some(notice) = self.clipboard.notice() {
            format!(" {} ", clipped(&plain(notice), cols.saturating_sub(2)))
        } else { format!(" {} {} {} ", counts, battery, clock) };
        let right_width = right.width().min(cols);
        let available = cols.saturating_sub(right_width);
        let host = plain(self.view["host"].as_str().unwrap_or(""));
        let mode = match self.mode.mode {
            InputMode::Locked | InputMode::Normal => " ",
            InputMode::Tmux => " PREFIX ",
            InputMode::Resize => " RESIZE ",
            InputMode::Move => " MOVE ",
            InputMode::Tab => " TAB ",
            InputMode::RenameTab => " RENAME TAB ",
            InputMode::Scroll => " SCROLL ",
            InputMode::EnterSearch | InputMode::Search => " SEARCH ",
            _ => " MODE ",
        };
        let mut used = 0;
        print!("\x1b[{}m", if dimmed { 3 } else { 23 });
        print!("\x1b[48;2;46;52;64m\x1b[38;2;136;192;208m");
        let heading = format!("{}{} │", mode, host);
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
            let name = clipped(&tab_name(tab, &self.panes, None, &self.view["auto_titles"]), name_budget);
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
