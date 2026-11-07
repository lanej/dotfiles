mod commands;
mod completion;
mod palette;

use std::{
    collections::{BTreeMap, VecDeque},
    path::PathBuf,
};
use zellij_tile::prelude::{actions::Action, *};

const OPEN: &str = "command-prompt";

enum Parsed {
    Native(commands::Parsed),
    Pane(PaneId),
    Tab(usize),
    Session(String),
}

fn parse(line: &str, cwd: PathBuf) -> Result<Parsed, String> {
    let words = shlex::split(line.trim().trim_start_matches(':'))
        .ok_or("Unclosed quote or trailing escape. Use quotes around names with spaces.")?;
    let name = words.first().map(String::as_str).unwrap_or("");
    if matches!(name, "focus-pane-id" | "go-to-tab-by-id" | "switch-session") {
        if words.len() != 2 || words[1].starts_with('-') {
            return Err(format!(
                "Usage: {name} <{}>",
                if name == "switch-session" {
                    "session-name"
                } else {
                    "id"
                }
            ));
        }
        let value = &words[1];
        return match name {
            "focus-pane-id" => {
                let (plugin, id) = if let Some(id) = value.strip_prefix("plugin_") {
                    (true, id)
                } else {
                    (false, value.strip_prefix("terminal_").unwrap_or(value))
                };
                let id = id
                    .parse::<u32>()
                    .map_err(|_| "Expected a pane ID such as terminal_3 or plugin_2".to_owned())?;
                Ok(Parsed::Pane(if plugin {
                    PaneId::Plugin(id)
                } else {
                    PaneId::Terminal(id)
                }))
            }
            "go-to-tab-by-id" => value
                .parse()
                .map(Parsed::Tab)
                .map_err(|_| "Expected a numeric tab ID".into()),
            _ => Ok(Parsed::Session(value.clone())),
        };
    }
    commands::parse(line, cwd).map(Parsed::Native)
}

#[derive(Default)]
struct CommandPrompt {
    allowed: bool,
    plugin_id: u32,
    client_id: ClientId,
    request: u64,
    origin: Option<(usize, PaneId)>,
    line: String,
    history: VecDeque<String>,
    actions: VecDeque<Action>,
    action_pending: bool,
    palette: Option<palette::Palette>,
}

register_plugin!(CommandPrompt);

impl ZellijPlugin for CommandPrompt {
    fn load(&mut self, configuration: BTreeMap<String, String>) {
        let ids = get_plugin_ids();
        self.plugin_id = ids.plugin_id;
        self.client_id = ids.client_id;
        if let Some(open) = configuration
            .get("palette")
            .and_then(|s| serde_json::from_str(s).ok())
        {
            self.palette = Some(palette::Palette::new(open));
            subscribe(&[
                EventType::Key,
                EventType::PaneUpdate,
                EventType::TabUpdate,
                EventType::SessionUpdate,
                EventType::PastedText,
            ]);
        } else {
            subscribe(&[EventType::InitialKeybinds, EventType::ActionComplete]);
        }
        subscribe(&[EventType::PermissionRequestResult]);
        request_permission(&[
            PermissionType::ReadApplicationState,
            PermissionType::OpenTerminalsOrPlugins,
            PermissionType::RunActionsAsUser,
            PermissionType::Reconfigure,
            PermissionType::ChangeApplicationState,
            PermissionType::MessageAndLaunchOtherPlugins,
        ]);
    }

    fn update(&mut self, event: Event) -> bool {
        if let Some(palette) = self.palette.as_mut() {
            return palette.update(event);
        }
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                self.allowed = true;
                hide_self();
                self.bind();
            }
            Event::PermissionRequestResult(PermissionStatus::Denied) => self.allowed = false,
            Event::InitialKeybinds(_) if self.allowed => self.bind(),
            Event::ActionComplete(_, _, context)
                if self.action_pending
                    && context.get("owner").map(String::as_str) == Some(OPEN) =>
            {
                self.action_pending = false;
                self.dispatch();
            }
            _ => {}
        }
        false
    }

    fn pipe(&mut self, message: PipeMessage) -> bool {
        if !self.allowed || self.palette.is_some() || !message.is_private || self.action_pending {
            return false;
        }
        if message.source == PipeSource::Keybind
            && message.name == OPEN
            && message.payload.as_deref() == Some(self.client_id.to_string().as_str())
        {
            match get_focused_pane_info() {
                Ok(origin) => {
                    self.origin = Some(origin);
                    self.line.clear();
                    self.input(String::new());
                }
                Err(error) => {
                    prompt(PromptRequest::notify(error).timeout(std::time::Duration::from_secs(4)));
                }
            }
        } else if matches!(message.source, PipeSource::Plugin(_)) && message.name == palette::REPLY
        {
            if let Some(reply) = message
                .payload
                .and_then(|s| serde_json::from_str::<palette::Reply>(&s).ok())
            {
                if reply.request == self.request
                    && reply.client == self.client_id
                    && self.origin.is_some()
                {
                    // Consume once. A late reply from a replaced popup cannot run.
                    self.request += 1;
                    self.line = reply.line;
                    self.execute();
                }
            }
        }
        false
    }

    fn render(&mut self, rows: usize, cols: usize) {
        if let Some(palette) = self.palette.as_mut() {
            palette.render(rows, cols);
        }
    }
}

impl CommandPrompt {
    fn bind(&self) {
        reconfigure(format!(
            "keybinds {{\n tmux {{\n bind \":\" {{\n MessagePluginId {} {{ name \"{OPEN}\"; payload \"{}\"; }}\n SwitchToMode \"Locked\";\n }}\n }}\n }}\n",
            self.plugin_id, self.client_id,
        ), false);
    }

    fn input(&mut self, error: String) {
        let Some(origin) = self.origin else {
            return;
        };
        self.request += 1;
        palette::launch(palette::Open {
            owner: self.plugin_id,
            client: self.client_id,
            request: self.request,
            origin,
            line: self.line.clone(),
            history: self.history.iter().cloned().collect(),
            error,
        });
    }

    fn execute(&mut self) {
        let Some(origin) = self.origin else {
            return;
        };
        if get_focused_pane_info().ok() != Some(origin) || get_pane_info(origin.1).is_none() {
            self.origin = None;
            prompt(
                PromptRequest::notify(
                    "The original pane or tab changed. Reopen : in the intended pane.",
                )
                .timeout(std::time::Duration::from_secs(4)),
            );
            return;
        }
        let cwd = match get_pane_cwd(origin.1) {
            Ok(cwd) => cwd,
            Err(error) => {
                self.input(error);
                return;
            }
        };
        let result = match parse(&self.line, cwd) {
            Ok(Parsed::Native(commands::Parsed::Actions(actions))) => {
                self.actions = actions.into();
                self.dispatch();
                Ok(())
            }
            Ok(Parsed::Native(commands::Parsed::Help(_))) => Ok(()),
            Ok(Parsed::Pane(id)) => {
                if get_pane_info(id).is_some_and(|p| p.is_selectable && !p.is_suppressed) {
                    focus_pane_with_id(id, false, false);
                    self.origin = None;
                    Ok(())
                } else {
                    Err(
                        "That pane is no longer available. Use list-panes to choose a live target."
                            .into(),
                    )
                }
            }
            Ok(Parsed::Tab(id)) => {
                if let Some(tab) = get_tab_info(id) {
                    switch_tab_to((tab.position + 1) as u32);
                    self.origin = None;
                    Ok(())
                } else {
                    Err(
                        "That tab is no longer available. Use list-tabs to choose a live target."
                            .into(),
                    )
                }
            }
            Ok(Parsed::Session(name)) => match get_session_list() {
                Ok(snapshot) if snapshot.live_sessions.iter().any(|s| s.name == name) => {
                    switch_session(Some(&name));
                    self.origin = None;
                    Ok(())
                }
                Ok(_) => Err(
                    "That session is no longer running. Use list-sessions to choose a live target."
                        .into(),
                ),
                Err(error) => Err(error),
            },
            Err(error) => Err(error),
        };
        match result {
            Ok(()) => {
                self.history.retain(|old| old != &self.line);
                self.history.push_front(self.line.clone());
                self.history.truncate(32);
            }
            Err(error) => self.input(error),
        }
    }

    fn dispatch(&mut self) {
        if let Some(action) = self.actions.pop_front() {
            self.action_pending = true;
            run_action(action, BTreeMap::from([("owner".into(), OPEN.into())]));
        } else {
            self.origin = None;
        }
    }
}
