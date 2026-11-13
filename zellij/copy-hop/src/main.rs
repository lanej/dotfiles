use copy_mode::{request::Operation, Label, Labels, Request, Snapshot, Target};
use std::collections::BTreeMap;
use zellij_tile::prelude::*;

const ALPHABET: &[u8] = b"asdfghjklqwertyuiopzxcvbnm";

#[derive(Default)]
struct Hop {
    permitted: bool,
    plugin_id: u32,
    client_id: ClientId,
    snapshot: Option<Snapshot>,
    started: Option<std::time::Instant>,
    matches: Vec<copy_mode::Cell>,
    page: usize,
    choosing: bool,
}

register_plugin!(Hop);

fn request(operation: Operation) -> Result<Option<Snapshot>, String> {
    copy_mode(Request {
        operation: Some(operation),
    })
}

impl Hop {
    fn bind(&self) {
        // rationale: KDL retains the pipe target and client payload omitted by RebindKeys.
        reconfigure(
            format!(
                "keybinds {{\n copy {{\n bind \"s\" {{\n MessagePluginId {} {{ name \"hop\"; payload \"{}\"; }}\n }}\n }}\n }}",
                self.plugin_id, self.client_id
            ),
            false,
        );
    }

    fn cancel(&mut self) {
        if let Some(snapshot) = self.snapshot.take() {
            let _ = request(Operation::ClearLabels(snapshot.session_id));
            clear_key_presses_intercepts();
        }
        self.started = None;
        self.matches.clear();
        self.choosing = false;
        self.page = 0;
    }

    fn begin(&mut self) {
        self.cancel();
        if let Ok(Some(snapshot)) = request(Operation::Read(true)) {
            let token = snapshot.session_id;
            self.snapshot = Some(snapshot);
            self.started = Some(std::time::Instant::now());
            set_timeout(15.0);
            intercept_key_presses();
            if request(Operation::SetLabels(Labels {
                session_id: token,
                labels: vec![],
            }))
            .is_err()
            {
                self.cancel();
            }
        }
    }

    fn show_labels(&mut self) {
        let Some(snapshot) = &self.snapshot else {
            return;
        };
        let labels = self
            .matches
            .iter()
            .skip(self.page * ALPHABET.len())
            .take(ALPHABET.len())
            .zip(ALPHABET)
            .map(|(cell, label)| Label {
                row: cell.row,
                column: cell.column,
                text: (*label as char).to_string(),
            })
            .collect();
        if request(Operation::SetLabels(Labels {
            session_id: snapshot.session_id,
            labels,
        }))
        .is_err()
        {
            self.cancel();
        }
    }

    fn key(&mut self, key: &str) {
        let Some(snapshot) = &self.snapshot else {
            return;
        };
        if self.choosing && key == "TAB" {
            self.page = (self.page + 1) % self.matches.len().div_ceil(ALPHABET.len());
            self.show_labels();
            return;
        }
        if key.chars().count() != 1 || key.chars().next().is_some_and(char::is_control) {
            self.cancel();
            return;
        }
        if !self.choosing {
            self.matches = snapshot
                .cells
                .iter()
                .filter(|cell| cell.text.starts_with(key))
                .cloned()
                .collect();
            if self.matches.is_empty() {
                self.cancel();
                return;
            }
            self.choosing = true;
            self.show_labels();
        } else {
            if let Some(index) = ALPHABET.iter().position(|label| key.as_bytes() == [*label]) {
                if let Some(target) = self.matches.get(self.page * ALPHABET.len() + index) {
                    let _ = request(Operation::MoveCursor(Target {
                        session_id: snapshot.session_id,
                        row: target.row,
                        column: target.column,
                    }));
                }
            }
            self.cancel();
        }
    }
}

impl ZellijPlugin for Hop {
    fn load(&mut self, _: BTreeMap<String, String>) {
        let ids = get_plugin_ids();
        self.plugin_id = ids.plugin_id;
        self.client_id = ids.client_id;
        subscribe(&[
            EventType::PermissionRequestResult,
            EventType::InitialKeybinds,
            EventType::CustomMessage,
            EventType::InterceptedKeyPress,
            EventType::ModeUpdate,
            EventType::Timer,
        ]);
        request_permission(&[
            PermissionType::Reconfigure,
            PermissionType::ReadPaneContents,
            PermissionType::ChangeApplicationState,
            PermissionType::InterceptInput,
            PermissionType::ReadApplicationState,
        ]);
    }

    fn pipe(&mut self, message: PipeMessage) -> bool {
        if self.permitted
            && message.is_private
            && message.source == PipeSource::Keybind
            && message.name == "hop"
            && message.payload.as_deref() == Some(self.client_id.to_string().as_str())
        {
            self.begin();
        }
        false
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(status) => {
                self.permitted = status == PermissionStatus::Granted;
                if self.permitted {
                    self.bind();
                } else {
                    self.cancel();
                }
            }
            Event::InitialKeybinds(_) if self.permitted => self.bind(),
            Event::CustomMessage(name, payload) if name == "copy_mode_key" => {
                if let Some((token, key)) = payload.split_once(':') {
                    if let Ok(token) = token.parse::<u64>() {
                        if self
                            .snapshot
                            .as_ref()
                            .is_some_and(|snapshot| snapshot.session_id == token)
                        {
                            self.key(key);
                        }
                    }
                }
            }
            Event::InterceptedKeyPress(key) => {
                let text = match key.bare_key {
                    BareKey::Char(c) if key.key_modifiers.is_empty() => c.to_string(),
                    BareKey::Char(c)
                        if key.key_modifiers.len() == 1
                            && key.key_modifiers.contains(&KeyModifier::Shift) =>
                    {
                        c.to_uppercase().collect()
                    }
                    _ => key.to_string(),
                };
                self.key(&text);
            }
            Event::ModeUpdate(mode) if mode.mode != InputMode::Copy => self.cancel(),
            Event::Timer(_) => {
                if let Some(started) = self.started {
                    let remaining = 15.0 - started.elapsed().as_secs_f64();
                    if remaining <= 0.0 {
                        self.cancel();
                    } else {
                        set_timeout(remaining);
                    }
                }
            }
            _ => {}
        }
        false
    }
}
