use serde_json::{json, Value};
use std::collections::BTreeMap;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};
use zellij_tile::prelude::*;
mod clipboard;
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
    roots: BTreeMap<u32, i32>,
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

fn rank(state: &str, done: bool) -> u8 {
    match state {
        "approval" | "question" | "plan" | "failed" => 0,
        _ if done => 1,
        "thinking" | "tool" | "waiting" => 2,
        _ => 3,
    }
}

fn mark(state: &str, done: bool) -> (&str, &str) {
    match state {
        "question" => ("?", "235;203;139"),
        "approval" | "plan" => ("!", "235;203;139"),
        "failed" => ("×", "191;97;106"),
        _ if done => ("✓", "163;190;140"),
        "thinking" | "tool" | "waiting" => ("●", "136;192;208"),
        _ => ("·", "129;161;193"),
    }
}

impl State {
    fn poll(&mut self) {
        if self.clipboard_receiver || !self.allowed || self.busy {
            return;
        }
        // Client-targeted broadcasts stop when the last client detaches. The
        // native session snapshot still discovers new tabs/panes and removes
        // a closed leader, allowing a surviving bar to take over.
        if let Ok(snapshot) = get_session_list() {
            if let Some(session) = snapshot.live_sessions.into_iter().find(|s| s.is_current_session) {
                self.mode.session_name = Some(session.name);
                if !self.visible || session.connected_clients == 0 || self.panes.panes.is_empty() {
                    self.tabs = session.tabs;
                    self.panes = session.panes;
                }
            }
        }
        if self.mode.session_name.is_none() { return; }
        let ids = get_plugin_ids();
        // Keep one session-wide manifest current even when every client is
        // detached or the top bar is hidden by fullscreen. Other invisible
        // bars need not duplicate that background work.
        let leader = leader(&self.panes);
        if !self.visible && ids.plugin_id != leader { return; }
        let mut panes = Vec::new();
        self.roots.clear();
        for (position, entries) in &self.panes.panes {
            let Some(tab) = self.tabs.iter().find(|tab| tab.position == *position) else { continue };
            for pane in entries.iter().filter(|p| !p.is_plugin && !p.exited) {
                // PaneUpdate broadcasts stop with no connected clients. Query
                // the native pane directly so detached title changes are seen.
                let Some(current) = get_pane_info(PaneId::Terminal(pane.id)) else { continue };
                if let Ok(pid) = get_pane_pid(PaneId::Terminal(pane.id)) {
                    self.roots.insert(pane.id, pid);
                    panes.push(json!({"pane": pane.id, "root_pid": pid, "tab_id": tab.tab_id,
                        "tab_position": position, "title": current.title}));
                }
            }
        }
        let manifest = json!({"server_pid": ids.zellij_pid, "session": self.mode.session_name,
            "panes": panes}).to_string();
        run_command(&["zellij-status", "view", &manifest], BTreeMap::new());
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
        EventType::SessionUpdate, EventType::ListClients]);
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
                if !self.allowed {
                    self.allowed = true;
                    if self.clipboard_receiver {
                        self.mode.session_name = sessions.iter().find(|session| session.is_current_session)
                            .map(|session| session.name.clone());
                    }
                    self.poll();
                }
            }
            Event::ListClients(_) if self.allowed && !self.clipboard_receiver => self.clients.finish(),
            Event::ModeUpdate(mode) => { self.mode = mode; self.poll(); }
            Event::TabUpdate(tabs) => { self.tabs = tabs; }
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
        if self.allowed {
            if self.clipboard_receiver {
                self.clipboard.route_binding(bindings_changed);
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
        let ids = get_plugin_ids();
        let records = self.view["records"].as_array().cloned().unwrap_or_default();
        let relevant: Vec<_> = records.iter().filter(|r| r["server_pid"].as_u64() == Some(ids.zellij_pid as u64)
            && r["pane"].as_u64().and_then(|id| self.roots.get(&(id as u32)))
                .map(|pid| Some(*pid as i64) == r["root_pid"].as_i64()).unwrap_or(false)).collect();
        let attention = records.iter().filter(|r| rank(r["state"].as_str().unwrap_or(""), r["result_ready"].as_bool().unwrap_or(false)) <= 1).count();
        let working = records.iter().filter(|r| rank(r["state"].as_str().unwrap_or(""), false) == 2).count();
        let clock = plain(self.view["clock"].as_str().unwrap_or(""));
        let battery = plain(self.view["battery"].as_str().unwrap_or(""));
        let counts = if self.view["available"].as_bool() == Some(true) {
            format!("!{} ●{}", attention, working)
        } else { "!? ●? broker?".into() };
        let right = if let Some(notice) = self.clipboard.notice() {
            format!(" {} ", clipped(&plain(notice), cols.saturating_sub(2)))
        } else { format!(" {} {} {} ", counts, battery, clock) };
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
            let record = relevant.iter().filter(|r| r["tab_id"].as_u64() == Some(tab.tab_id as u64))
                .min_by_key(|r| rank(r["state"].as_str().unwrap_or(""), r["result_ready"].as_bool().unwrap_or(false)));
            let (glyph, color) = record.map(|r| mark(r["state"].as_str().unwrap_or(""), r["result_ready"].as_bool().unwrap_or(false)))
                .unwrap_or(if tab.has_bell_notification { ("!", "235;203;139") } else { ("", "136;192;208") });
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
