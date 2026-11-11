mod theme;
mod bar;
use theme::{foreground, background};
use lane_zellij_protocol::{ReloadRequest, ReloadAck, ReadinessRequest, ReadinessReply,
    StatusView, MAX_CONFIG_BYTES, READINESS};
use std::collections::BTreeMap;
use unicode_width::{UnicodeWidthChar, UnicodeWidthStr};
use zellij_tile::prelude::*;
mod clipboard;
mod attention;
mod attention_policy;
mod clients;
mod notifications;
mod modules;

#[derive(Default)]
struct State {
    mode: ModeInfo,
    tabs: Vec<TabInfo>,
    panes: PaneManifest,
    view: StatusView,
    allowed: bool,
    visible: bool,
    busy: bool,
    title_refresh: bool,
    attention: GlobalAttention,
    attention_ready: bool,
    attention_config: attention_policy::Config,
    clicks: Vec<(usize, usize, u32)>,
    clipboard: clipboard::Clipboard,
    clipboard_receiver: bool,
    clipboard_prepared: bool,
    permissions_requested: bool,
    clients: clients::Clients,
    notifications: notifications::Notifications,
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

// Focus, output and attention changes do not change title ownership.
fn title_sources(panes: &PaneManifest) -> BTreeMap<(usize, u32), (&str, bool)> {
    panes.panes.iter().flat_map(|(position, panes)| panes.iter()
        .filter(|p| !p.is_plugin && !p.exited)
        .map(move |p| ((*position, p.id), (p.title.as_str(), !p.is_floating && !p.is_suppressed)))).collect()
}

fn tab_name(tab: &TabInfo, panes: &PaneManifest) -> String {
    if !tab.name.is_empty() && tab.name != format!("Tab #{}", tab.tab_id + 1) {
        return plain(&tab.name);
    }
    // Before the host commits a new automatic name, every client uses the same oldest pane.
    panes.panes.get(&tab.position).into_iter().flatten()
        .filter(|p| !p.is_plugin && !p.exited && !p.is_floating && !p.is_suppressed)
        .filter_map(|p| lane_zellij_protocol::titles::pane_label(&p.title).map(|title| (p.id, title)))
        .min_by_key(|(id, _)| *id).map(|(_, title)| title)
        .unwrap_or_else(|| format!("Tab #{}", tab.position))
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

impl State {
    fn poll(&mut self) {
        if self.clipboard_receiver || !self.allowed || self.busy || !self.visible { return; }
        // In rename mode ModeInfo holds a draft, not a queryable session name.
        if self.mode.mode == InputMode::RenameSession { return; }
        // Native Zellij owns attention, including detached sessions. The
        // helper supplies host metadata and lifecycle-checked title ownership.
        let Some(session) = self.mode.session_name.as_deref() else { return };
        let command = if std::mem::take(&mut self.title_refresh) { "refresh-view" } else { "view" };
        run_command(&["zellij-status", command, session], BTreeMap::from([("view".into(), command.into())]));
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
                // Session metadata contains the committed name; ModeUpdate
                // owns this client's editable draft until rename mode exits.
                if self.mode.mode != InputMode::RenameSession {
                    if self.mode.session_name != session { self.view = StatusView::default(); }
                    self.mode.session_name = session;
                }
                if !self.allowed {
                    self.allowed = true;
                    if self.clipboard_receiver { self.attention_config.load(); }
                    self.poll();
                }
            }
            Event::ListClients(_) if self.allowed && !self.clipboard_receiver => self.clients.finish(),
            Event::ModeUpdate(mut mode) => {
                if mode.session_name.is_none() { mode.session_name = self.mode.session_name.clone(); }
                if self.mode.session_name != mode.session_name { self.view = StatusView::default(); }
                self.mode = mode; self.poll();
            }
            Event::TabUpdate(tabs) => { self.tabs = tabs; }
            Event::GlobalAttentionUpdate(attention) => {
                if self.allowed && !self.clipboard_receiver {
                    let focused = if self.visible { get_focused_pane_info().ok().map(|(_, pane)| pane) } else { None };
                    let active = self.visible && self.mode.session_ascended != Some(true)
                        && self.mode.session_dimmed != Some(true);
                    self.notifications.observe(&attention, get_plugin_ids().zellij_pid, focused, active,
                        get_plugin_ids().plugin_id == leader(&self.panes));
                }
                self.attention = attention;
                self.attention_ready = true;
            }
            Event::PaneUpdate(panes) => {
                self.title_refresh |= title_sources(&panes) != title_sources(&self.panes);
                self.panes = panes;
                if self.title_refresh { self.poll(); }
            }
            Event::Visible(visible) => { self.visible = visible; if visible { self.poll(); } }
            Event::Timer(_) => { self.clipboard.tick(); self.poll(); set_timeout(1.0); }
            Event::RunCommandResult(code, _out, error, context)
                if context.get("action").map(String::as_str) == Some(notifications::RECORD) => {
                self.notifications.finish(code, &error, &context);
            }
            Event::RunCommandResult(code, out, error, context)
                if context.get("action").map(String::as_str) == Some(attention_policy::LOAD) => {
                if self.clipboard_receiver {
                    if let Some(error) = self.attention_config.finish(code, &out, &error, &context) {
                        eprintln!("lane-status attention: {error}");
                        let error: String = error.chars().filter(|c| !c.is_control()).take(180).collect();
                        self.clipboard.publish_notice(&format!("attention: {error}; using defaults"));
                    }
                }
            }
            Event::RunCommandResult(code, out, error, context)
                if context.get("action").map(String::as_str) == Some(clipboard::MESSAGE) => {
                // Native client-attach replay can broadcast cached results.
                if context.get("client") == Some(&get_plugin_ids().client_id.to_string()) {
                    self.clipboard.finish(code, out, error);
                }
            }
            Event::RunCommandResult(code, out, error, context) => {
                self.busy = false;
                if context.get("view").map(String::as_str) == Some("refresh-view") && code != Some(0) {
                    self.title_refresh = true;
                    return false;
                }
                self.view = if code == Some(0) {
                    serde_json::from_slice::<StatusView>(&out).ok()
                        .filter(|v| v.session == self.mode.session_name).unwrap_or_default()
                } else {
                    eprintln!("lane-status helper failed: {}", String::from_utf8_lossy(&error));
                    StatusView::default()
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
        if self.clipboard_receiver && self.allowed && message.name == READINESS {
            if let PipeSource::Cli(pipe) = &message.source {
                if let Some(payload) = message.payload.as_deref().filter(|text| text.len() <= 1024) {
                    if let Ok(request) = serde_json::from_str::<ReadinessRequest>(payload) {
                        let ids = get_plugin_ids();
                        if request.plugin_id == ids.plugin_id
                            && !request.request.is_empty() && request.request.len() <= 128 {
                            let reply = ReadinessReply { request: request.request,
                                plugin_id: ids.plugin_id, client_id: ids.client_id as u32,
                                config_ready: self.attention_config.ready,
                                attention_ready: self.attention_ready,
                                bindings_installed: self.clipboard.bindings_installed() };
                            if let Ok(reply) = serde_json::to_string(&reply) {
                                cli_pipe_output(pipe, &(reply + "\n"));
                            }
                        }
                    }
                }
            }
            return false;
        }
        if self.clipboard_receiver && self.allowed && message.name == attention_policy::RELOAD {
            if let PipeSource::Cli(pipe) = &message.source {
                // Only the discovered persistent receiver handles reloads.
                // Ignore the trailing CLI EOF message and unrelated instances.
                if let Some(payload) = message.payload.as_deref().filter(|text| text.len() <= MAX_CONFIG_BYTES) {
                    if let Ok(request) = serde_json::from_str::<ReloadRequest>(payload) {
                        let ids = get_plugin_ids();
                        if request.plugin_id == ids.plugin_id
                            && !request.request.is_empty() && request.request.len() <= 128 {
                            let mut reply = ReloadAck { request: request.request,
                                plugin_id: ids.plugin_id, client_id: ids.client_id as u32,
                                ok: None, error: None };
                            match self.attention_config.apply(&request.priority) {
                                Ok(()) => reply.ok = Some(true),
                                Err(error) => reply.error = Some(error),
                            }
                            if let Ok(reply) = serde_json::to_string(&reply) {
                                cli_pipe_output(pipe, &(reply + "\n"));
                            }
                        }
                    }
                }
            }
            return false;
        }
        if self.allowed && !self.clipboard_receiver && matches!(message.source, PipeSource::Cli(_)) {
            if matches!(message.name.as_str(), notifications::SEND | notifications::VALIDATE) {
                return self.notifications.pipe(&message, self.mode.session_name.as_deref(),
                    get_plugin_ids().plugin_id == leader(&self.panes));
            }
            return self.clients.pipe(&message, &self.panes);
        }
        if matches!(message.source, PipeSource::Plugin(_)) {
            if !self.clipboard_receiver && self.allowed && message.name == notifications::ERROR {
                return self.notifications.receive_error(&message);
            }
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
            && self.attention_config.ready
            && matches!(message.name.as_str(), attention::MESSAGE | attention::HIGHEST) {
            attention::jump(&self.tabs, &self.attention, &message, &self.attention_config.policy);
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
        let colors = self.mode.style.colors;
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
            print!("\x1b[1;23;{};{}m{}{}\x1b[0m",
                background(colors.ribbon_selected.background), foreground(colors.ribbon_selected.base), label, " ".repeat(cols.saturating_sub(label.width())));
            return;
        }
        if self.mode.mode == InputMode::RenameSession && !dimmed {
            // ModeInfo carries the native per-client draft, not the committed
            // session name. Native Enter/cancel/validation own its lifecycle.
            let draft = plain(self.mode.session_name.as_deref().unwrap_or(""));
            let label = clipped(&format!(" RENAME SESSION: {}  |  Enter saves · Esc cancels ", draft), cols);
            print!("\x1b[1;23;{};{}m{}{}\x1b[0m",
                background(colors.ribbon_selected.background), foreground(colors.ribbon_selected.base), label, " ".repeat(cols.saturating_sub(label.width())));
            return;
        }
        self.render_bar(cols, dimmed);
    }
}
