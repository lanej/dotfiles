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
                let Ok((tab_id, pane_id)) = get_focused_pane_info() else { return false };
                let tab = get_tab_info(tab_id);
                let pane = get_pane_info(pane_id);
                let row = json!({"token": self.token(),
                    "tab": tab.map(|tab| format!("{}: {}", tab.position, tab.name)),
                    "pane": pane.map(|pane| pane.title)});
                cli_pipe_output(pipe, &(row.to_string() + "\n"));
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
