use std::{collections::BTreeMap, path::Path};
use zellij_tile::prelude::actions::Action;
use zellij_tile::prelude::*;

#[derive(Default)]
struct Navigation {
    permitted: bool,
    plugin_id: u32,
    client_id: ClientId,
    diagnostic_server_pid: u32,
}

register_plugin!(Navigation);

impl ZellijPlugin for Navigation {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        let ids = get_plugin_ids();
        self.plugin_id = ids.plugin_id;
        self.client_id = ids.client_id;
        self.diagnostic_server_pid = ids.zellij_pid;
        eprintln!("popup-diagnostic navigation request server={} plugin={} client={}", self.diagnostic_server_pid, self.plugin_id, self.client_id);
        subscribe(&[
            EventType::PermissionRequestResult,
            EventType::InitialKeybinds,
        ]);
        request_permission(&[
            PermissionType::ReadApplicationState,
            PermissionType::ChangeApplicationState,
            PermissionType::WriteToStdin,
            PermissionType::Reconfigure,
        ]);
    }

    fn update(&mut self, event: Event) -> bool {
        match event {
            Event::PermissionRequestResult(status) => {
                eprintln!("popup-diagnostic navigation permission server={} plugin={} client={} status={:?}", self.diagnostic_server_pid, self.plugin_id, self.client_id, status);
                self.permitted = status == PermissionStatus::Granted;
                if self.permitted {
                    eprintln!("popup-diagnostic navigation hide-request server={} plugin={} client={}", self.diagnostic_server_pid, self.plugin_id, self.client_id);
                    hide_self();
                    reconfigure(self.bindings(), false);
                }
            }
            Event::InitialKeybinds(keybinds) if self.permitted => {
                // NOTE: Keybinding events omit pipe targets and payloads from their action protobuf.
                let missing = [InputMode::Locked, InputMode::Normal].iter().any(|mode| {
                    let bound = keybinds
                        .iter()
                        .find(|(bound_mode, _)| bound_mode == mode)
                        .map(|(_, keys)| keys.as_slice())
                        .unwrap_or(&[]);
                    ['h', 'j', 'k', 'l'].iter().any(|key| {
                        !bound.iter().any(|(bound_key, actions)| {
                            *bound_key
                                == KeyWithModifier::new(BareKey::Char(*key)).with_ctrl_modifier()
                                && matches!(actions.as_slice(), [Action::KeybindPipe { .. }])
                        })
                    })
                });
                if missing {
                    reconfigure(self.bindings(), false);
                }
            }
            _ => {}
        }
        false
    }

    fn pipe(&mut self, message: PipeMessage) -> bool {
        // WHY: URL/alias messages can broadcast; bind and verify the originating client.
        let own_client = self.client_id.to_string();
        if self.permitted
            && message.source == PipeSource::Keybind
            && message.payload.as_deref() == Some(own_client.as_str())
        {
            if let Err(error) = navigate(&message.name) {
                eprintln!("pane-navigation: {error}");
            }
        }
        false
    }
}

impl Navigation {
    fn bindings(&self) -> String {
        // WHY: RebindKeys drops pipe targets in protobuf; KDL preserves MessagePluginId.
        let mut config = String::from("keybinds {\n shared_among \"locked\" \"normal\" {\n");
        for (key, direction) in [('h', "left"), ('j', "down"), ('k', "up"), ('l', "right")] {
            config.push_str(&format!(
                "bind \"Ctrl {key}\" {{\n MessagePluginId {} {{ name \"{direction}\"; payload \"{}\"; }}\n}}\n",
                self.plugin_id, self.client_id
            ));
        }
        config.push_str("}\n}\n");
        config
    }
}

fn navigate(name: &str) -> Result<(), String> {
    let (direction, key) = match name {
        "left" => (Direction::Left, 8),
        "down" => (Direction::Down, 10),
        "up" => (Direction::Up, 11),
        "right" => (Direction::Right, 12),
        _ => return Ok(()),
    };
    let source = get_focused_pane_info()?;
    if !matches!(source.1, PaneId::Terminal(_)) {
        return Ok(());
    }
    let command = get_pane_running_command(source.1)?;
    let executable = command
        .first()
        .and_then(|argument| Path::new(argument).file_name())
        .and_then(|name| name.to_str())
        .ok_or("No foreground command")?;
    let forward = matches!(
        executable,
        "vi" | "vim"
            | "nvim"
            | "view"
            | "gview"
            | "gvim"
            | "vimdiff"
            | "nvimdiff"
            | "gvimdiff"
            | "tmux"
            | "zellij"
    );
    let pane = get_pane_info(source.1).ok_or("The source pane disappeared")?;
    // WHY: Queries can yield to other input; never act on a different pane or tab.
    if get_focused_pane_info()? != source {
        return Err("Focus changed during navigation".into());
    }
    if forward {
        write_to_pane_id(vec![key], source.1);
    } else if !pane.is_fullscreen {
        move_focus(direction);
    }
    Ok(())
}
