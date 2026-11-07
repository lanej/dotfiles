mod commands;

use std::collections::{BTreeMap, VecDeque};
use zellij_tile::prelude::actions::Action;
use zellij_tile::prelude::*;

const OPEN: &str = "command-prompt";
const NEW_SESSION: &str = "new-session";

#[derive(Clone, Copy)]
enum Input {
    Command,
    Commands,
    History,
    Help,
}

#[derive(Default)]
struct CommandPrompt {
    allowed: bool,
    plugin_id: u32,
    client_id: ClientId,
    request: Option<(u64, Input)>,
    origin: Option<(usize, PaneId)>,
    line: String,
    history: VecDeque<String>,
    actions: VecDeque<Action>,
    action_pending: bool,
}

register_plugin!(CommandPrompt);

impl ZellijPlugin for CommandPrompt {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        let ids = get_plugin_ids();
        self.plugin_id = ids.plugin_id;
        self.client_id = ids.client_id;
        subscribe(&[
            EventType::PermissionRequestResult,
            EventType::InitialKeybinds,
            EventType::PromptResult,
            EventType::ActionComplete,
        ]);
        request_permission(&[
            PermissionType::ReadApplicationState,
            PermissionType::ChangeApplicationState,
            PermissionType::OpenTerminalsOrPlugins,
            PermissionType::RunActionsAsUser,
            PermissionType::Reconfigure,
        ]);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(PermissionStatus::Granted) => {
                self.allowed = true;
                hide_self();
                self.bind();
            }
            Event::PermissionRequestResult(PermissionStatus::Denied) => self.allowed = false,
            Event::InitialKeybinds(_) if self.allowed => {
                // The event omits pipe targets, so reapply the exact private
                // binding. Native config equality suppresses no-op updates.
                self.bind();
            }
            Event::PromptResult(id, result) if self.allowed => {
                if let Some((expected, input)) = self.request {
                    if id == expected {
                        self.request = None;
                        self.answer(input, result);
                    }
                }
            }
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
        if self.allowed
            && message.is_private
            && message.source == PipeSource::Keybind
            && matches!(message.name.as_str(), OPEN | NEW_SESSION)
            && message.payload.as_deref() == Some(self.client_id.to_string().as_str())
            && self.request.is_none()
            && !self.action_pending
        {
            match get_focused_pane_info() {
                Ok(origin) => {
                    if message.name == NEW_SESSION {
                        match get_pane_cwd(origin.1) {
                            Ok(cwd) => {
                                // This API treats /tmp, /host, /data and /cache
                                // as WASI aliases, but get_pane_cwd returns a
                                // host path. POSIX /.. is root on macOS/Linux;
                                // keep that component to avoid alias rewriting.
                                let Ok(relative) = cwd.strip_prefix("/") else {
                                    self.notice(
                                        "The focused pane has no absolute working directory."
                                            .into(),
                                    );
                                    return false;
                                };
                                let cwd = std::path::Path::new("/..").join(relative);
                                // Never reuse a popup's inline layout: its P key
                                // detaches instead of opening the shared popup.
                                switch_session_with_layout(
                                    None,
                                    LayoutInfo::File("tmux".into(), Default::default()),
                                    Some(cwd),
                                );
                            }
                            Err(error) => self.notice(error),
                        }
                        return false;
                    }
                    self.origin = Some(origin);
                    self.line.clear();
                    self.input("Zellij action. Enter help or history for a picker.");
                }
                Err(error) => self.notice(error),
            }
        }
        false
    }
}

impl CommandPrompt {
    fn bind(&self) {
        let bindings = [(":", OPEN), ("C", NEW_SESSION)]
            .into_iter()
            .map(|(key, name)| format!(
                "bind \"{key}\" {{\n MessagePluginId {} {{ name \"{name}\"; payload \"{}\"; }}\n SwitchToMode \"Locked\";\n }}",
                self.plugin_id, self.client_id,
            ))
            .collect::<Vec<_>>()
            .join("\n");
        reconfigure(
            format!("keybinds {{\n tmux {{\n {bindings}\n }}\n }}"),
            false,
        );
    }

    fn ask(&mut self, request: PromptRequest, input: Input) {
        let request = request
            .title("Zellij command :")
            .placement(PromptPlacement::Center)
            .capture_all_keys(true)
            .outside_click(OutsideClick::Close);
        self.request = Some((prompt(request), input));
    }

    fn input(&mut self, message: &str) {
        self.ask(
            PromptRequest::form(vec![FormField::input("command", ":")
                .placeholder("rename-tab \"work\"")
                .default_value(self.line.clone())])
            .message(message)
            .buttons("Run", "Cancel"),
            Input::Command,
        );
    }

    fn notice(&mut self, message: String) {
        self.ask(PromptRequest::info("Zellij command", message), Input::Help);
    }

    fn answer(&mut self, input: Input, result: PromptResult) {
        match (input, result) {
            (Input::Command, PromptResult::Answered(PromptValue::Form(mut fields))) => {
                let Some(PromptValue::Text(line)) = fields.remove("command") else {
                    self.origin = None;
                    return;
                };
                self.line = line;
                match self.line.trim() {
                    "help" => self.ask(PromptRequest::choose(commands::choices()), Input::Commands),
                    "history" => {
                        if self.history.is_empty() {
                            self.input("No commands in this client's session history yet.");
                        } else {
                            self.ask(
                                PromptRequest::choose(self.history.iter().cloned()),
                                Input::History,
                            );
                        }
                    }
                    "" => self.origin = None,
                    _ => self.execute(),
                }
            }
            (Input::Commands, PromptResult::Answered(PromptValue::Choice(command))) => {
                self.line = format!("{command} ");
                self.input("Add arguments, or --help for this command's options.");
            }
            (Input::History, PromptResult::Answered(PromptValue::Choice(command))) => {
                self.line = command;
                self.input("Review the command, then Enter to run it.");
            }
            (_, PromptResult::Error(error)) => {
                // Do not repeatedly re-open a native prompt that the runtime
                // cannot display (eg. an incompatible or missing prompt plugin).
                eprintln!("command-prompt: {error}");
                self.origin = None;
            }
            _ => self.origin = None,
        }
    }

    fn execute(&mut self) {
        let Some(origin) = self.origin else {
            return;
        };
        if get_focused_pane_info().ok() != Some(origin) || get_pane_info(origin.1).is_none() {
            self.origin = None;
            self.notice("The original pane or tab changed. Nothing ran; reopen the command prompt in the intended pane.".into());
            return;
        }
        let cwd = match get_pane_cwd(origin.1) {
            Ok(cwd) => cwd,
            Err(error) => {
                self.input(&error);
                return;
            }
        };
        match commands::parse(&self.line, cwd) {
            Ok(commands::Parsed::Help(help)) => self.notice(help),
            Ok(commands::Parsed::Actions(actions)) => {
                if !actions.is_empty() {
                    self.history.retain(|old| old != &self.line);
                    self.history.push_front(self.line.clone());
                    self.history.truncate(32);
                }
                self.actions = actions.into();
                self.dispatch();
            }
            Err(error) => self.input(&error),
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
