use serde_json::{json, Value};
use std::time::{SystemTime, UNIX_EPOCH};
use zellij_tile::prelude::*;

pub const SNAPSHOT: &str = "lane-client-snapshot";
pub const DETACH: &str = "lane-client-detach";
const SUPPORTED_RUNTIME: &str = "0.46.0";
const UNSUPPORTED_RUNTIME: &str = "The client chooser requires the pinned Zellij 0.46.0 server. Run make zellij-runtime and restart this session.";

#[derive(Default)]
pub struct Clients {
    nonce: String,
    supported_runtime: bool,
    pending: Option<(String, Value)>,
}

impl Clients {
    pub fn start(&mut self) {
        // Query the server hosting this plugin, not a possibly newer binary
        // on PATH while the current session still runs an older server.
        self.supported_runtime = get_zellij_version() == SUPPORTED_RUNTIME;
        // The pinned runtime allocates a fresh native ID for every attachment
        // and removes detached plugin instances. A nonce also invalidates a
        // chooser entry if this still-connected client's plugin is reloaded.
        self.nonce = SystemTime::now().duration_since(UNIX_EPOCH)
            .map(|time| time.as_nanos().to_string()).unwrap_or_default();
    }

    fn token(&self) -> Value {
        let ids = get_plugin_ids();
        json!({"client_id": ids.client_id, "plugin_id": ids.plugin_id,
            "server_pid": ids.zellij_pid, "nonce": self.nonce})
    }

    fn valid(&self, token: &Value) -> bool {
        self.supported_runtime && !self.nonce.is_empty() && *token == self.token()
    }

    pub fn pipe(&mut self, message: &PipeMessage, panes: &PaneManifest) -> bool {
        let PipeSource::Cli(pipe) = &message.source else { return false };
        match message.name.as_str() {
            SNAPSHOT if get_plugin_ids().plugin_id == crate::leader(panes) => {
                if !self.supported_runtime {
                    cli_pipe_output(pipe, &(json!({"error": UNSUPPORTED_RUNTIME}).to_string() + "\n"));
                    return false;
                }
                // The picker reads lifecycle-checked ownership once per
                // snapshot; hidden plugin clones do not poll host metadata.
                // A non-TTY CLI sends a trailing EOF message without payload.
                // It must not overwrite the ownership-aware snapshot rows.
                let Some(payload) = message.payload.as_deref() else { return false };
                let request: Value = serde_json::from_str(payload).unwrap_or_default();
                let owned = &request["auto_titles"];
                let Ok((tab_id, pane_id)) = get_focused_pane_info() else { return false };
                let tab = get_tab_info(tab_id);
                let Some(pane) = get_pane_info(pane_id) else { return false };
                let row = json!({"token": self.token(),
                    "tab": tab.map(|tab| format!("{}: {}", tab.position, crate::tab_name(&tab, panes, Some(&pane), owned))),
                    "pane_id": pane_id.to_string(),
                    "pane": pane.title});
                cli_pipe_output(pipe, &(row.to_string() + "\n"));
            }
            "lane-move-pane" => {
                let Ok(request) = serde_json::from_str::<Value>(message.payload.as_deref().unwrap_or("")) else {
                    return false;
                };
                let token = &request["token"];
                let ids = get_plugin_ids();
                if token["plugin_id"].as_u64() != Some(ids.plugin_id as u64)
                    || token["client_id"].as_u64() != Some(ids.client_id as u64) {
                    return false;
                }
                let result = self.move_pane(&request);
                cli_pipe_output(pipe, &(result.unwrap_or_else(|error| error.to_owned()) + "\n"));
            }
            DETACH => {
                let Ok(token) = serde_json::from_str::<Value>(message.payload.as_deref().unwrap_or("")) else {
                    return false;
                };
                let ids = get_plugin_ids();
                if token["plugin_id"].as_u64() != Some(ids.plugin_id as u64)
                    || token["client_id"].as_u64() != Some(ids.client_id as u64) {
                    return false;
                }
                if !self.supported_runtime {
                    cli_pipe_output(pipe, &(UNSUPPORTED_RUNTIME.to_owned() + "\n"));
                } else if !self.valid(&token) {
                    cli_pipe_output(pipe, "The selected attachment changed; reopen the client chooser.\n");
                } else if self.pending.is_some() {
                    cli_pipe_output(pipe, "A detach request is already pending for this client.\n");
                } else {
                    // Keep the CLI alive through an asynchronous native
                    // round trip before the final identity and focus check.
                    block_cli_pipe_input(pipe);
                    self.pending = Some((pipe.clone(), token));
                    list_clients();
                }
            }
            _ => return false,
        }
        false
    }

    fn move_pane(&self, request: &Value) -> Result<String, &'static str> {
        if !self.valid(&request["token"]) {
            return Err("The selected attachment changed; reopen the move picker");
        }
        let source = request["source"].as_u64().and_then(|id| u32::try_from(id).ok())
            .ok_or("Invalid source pane")?;
        let picker = request["picker"].as_u64().and_then(|id| u32::try_from(id).ok())
            .ok_or("Invalid picker pane")?;
        let source_tab = request["source_tab"].as_u64().ok_or("Invalid source tab")? as usize;
        let source_id = PaneId::Terminal(source);
        let pane = get_pane_info(source_id).ok_or("The original pane closed")?;
        if source == picker || pane.exited || pane.is_suppressed {
            return Err("The original pane changed; reopen the move picker");
        }
        let destination = if request["destination"].is_null() { None } else {
            let id = request["destination"].as_u64().ok_or("Invalid destination tab")? as usize;
            get_tab_info(id).ok_or("The destination tab closed; reopen the move picker")?;
            Some(id)
        };
        // Native queries can yield. Confirm the requesting client still owns
        // this picker; never use the globally focused pane for the transfer.
        if get_focused_pane_info().ok() != Some((source_tab, PaneId::Terminal(picker))) {
            return Err("Picker focus changed; reopen the move picker");
        }
        let result = (|| {
            let moved = match destination {
                Some(id) if id == source_tab => Some(id),
                Some(id) => {
                    // The pinned BreakPanes APIs mix IDs and positions. Reserve a
                    // new split, then replace only that owned pane by native ID.
                    let tab = get_tab_info(id).ok_or("The destination tab closed")?;
                    go_to_tab(tab.position as u32);
                    if get_focused_pane_info().ok().map(|focus| focus.0) != Some(id) {
                        return Err("The destination changed; original pane was not moved");
                    }
                    // A held inert command uses the existing RunCommands grant;
                    // no login/interactive shell hooks can rename the destination.
                    let placeholder = open_command_pane(
                        CommandToRun::new_with_args("/bin/sh", vec!["-c", ":"]),
                        Default::default(),
                    ).ok_or("Could not create a destination split")?;
                    focus_pane_with_id(placeholder, false, false);
                    if get_focused_pane_info().ok() != Some((id, placeholder)) {
                        close_pane_with_id(placeholder);
                        return Err("The destination changed; original pane was not moved");
                    }
                    replace_pane_with_existing_pane(placeholder, source_id, false);
                    if get_pane_info(placeholder).is_some() {
                        close_pane_with_id(placeholder);
                        return Err("Could not place the original pane in the destination split");
                    }
                    Some(id)
                },
                None => break_panes_to_new_tab(&[source_id], None, true),
            };
            let expected_tab = destination.or(moved).ok_or("Zellij could not transfer the pane")?;
            focus_terminal_pane(source, false, false);
            if get_focused_pane_info().ok() != Some((expected_tab, source_id)) {
                return Err("The destination changed during transfer; inspect the pane before retrying");
            }
            Ok("moved".to_owned())
        })();
        if result.is_err() && get_pane_info(PaneId::Terminal(picker)).is_some() {
            // Errors are printed in the chooser, which remains in its source tab.
            focus_terminal_pane(picker, false, false);
        }
        result
    }

    pub fn finish(&mut self) {
        let Some((pipe, token)) = self.pending.take() else { return };
        // The focused-pane query reaches the screen directly and also covers
        // scrollback-editor clients omitted by native ListClients metadata.
        // SessionUpdate can replay stale cached membership. Native attachment
        // IDs and this instance's nonce remain stable across those snapshots.
        if self.valid(&token) && get_focused_pane_info().is_ok() {
            detach();
            cli_pipe_output(&pipe, "detached\n");
        } else {
            cli_pipe_output(&pipe, "The selected attachment changed; reopen the client chooser.\n");
        }
        unblock_cli_pipe_input(&pipe);
    }
}
